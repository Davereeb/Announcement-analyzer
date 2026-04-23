import asyncio
import io
import json
import re
import subprocess
import time
import zipfile
from html.parser import HTMLParser

import httpx
import pdfplumber

import config

# Shared cookie cache — solved once and reused across all concurrent requests
_cached_cookies: dict = {}
_cookie_lock = asyncio.Lock()   # 保证同一时间只有一个协程在解 JS 挑战


def _solve_js_challenge(js_body: str) -> dict:
    """Run the anti-bot JS challenge through Node.js and return cookie dict."""
    m = re.search(r"<script>(.*?)</script>", js_body, re.DOTALL)
    if not m:
        return {}
    script = m.group(1)
    wrapped = (
        "var _cookies = [];\n"
        "var document = {\n"
        "  get cookie() { return _cookies.join('; '); },\n"
        "  set cookie(v) { _cookies.push(v.replace(/;$/, '').trim()); }\n"
        "};\n"
        "var location = { href: 'http://x.com' };\n"
        "function setTimeout(fn, t) {}\n"
        + script
        + "\nconsole.log(JSON.stringify(_cookies));\n"
    )
    result = subprocess.run(
        ["node", "-e", wrapped], capture_output=True, text=True, timeout=5
    )
    if result.returncode != 0:
        return {}
    try:
        cookies_list = json.loads(result.stdout.strip())
    except Exception:
        return {}
    cookie_dict = {}
    for c in cookies_list:
        if "=" in c:
            k, v = c.split("=", 1)
            v = v.split(";")[0].strip().rstrip("#")
            cookie_dict[k.strip()] = v
    return cookie_dict


async def _refresh_cookies(client: httpx.AsyncClient, challenge_body: bytes, old_cookies: dict):
    """加锁解 JS 挑战，只有当 Cookie 未被其他协程更新时才重新解。"""
    global _cached_cookies
    async with _cookie_lock:
        # 如果已被其他协程更新（不再是触发挑战时的旧值），直接用新值
        if _cached_cookies and _cached_cookies != old_cookies:
            return
        js_body = challenge_body.decode("utf-8", errors="replace")
        new_cookies = _solve_js_challenge(js_body)
        if not new_cookies:
            raise ValueError("JS challenge could not be solved")
        _cached_cookies = new_cookies


async def _download_bytes(client: httpx.AsyncClient, url: str, cookies: dict) -> bytes:
    """流式下载，避免超大 PDF 被超时截断。"""
    chunks = []
    async with client.stream("GET", url, cookies=cookies, follow_redirects=True) as r:
        r.raise_for_status()
        async for chunk in r.aiter_bytes(chunk_size=1024 * 256):
            chunks.append(chunk)
    return b"".join(chunks)


async def fetch_pdf(url: str) -> tuple[str, float]:
    global _cached_cookies
    t0 = time.monotonic()

    # 超大文件给更长超时
    timeout = httpx.Timeout(connect=15, read=120, write=30, pool=10)
    async with httpx.AsyncClient(timeout=timeout) as client:
        current_cookies = _cached_cookies.copy()
        pdf_bytes = await _download_bytes(client, url, current_cookies)

        # 检测到 JS 挑战
        if pdf_bytes[:8].lstrip().startswith(b"<script>"):
            await _refresh_cookies(client, pdf_bytes, current_cookies)
            # 用新 Cookie 重试
            pdf_bytes = await _download_bytes(client, url, _cached_cookies)

    if pdf_bytes[:8].lstrip().startswith(b"<script>"):
        raise ValueError("Still receiving JS challenge after cookie solve")

    text = _extract_text(pdf_bytes)
    elapsed = time.monotonic() - t0
    return text, elapsed


def _extract_text(file_bytes: bytes) -> str:
    magic = file_bytes[:4]

    # PDF
    if magic == b"%PDF":
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return _clean_text("\n".join(pages))

    # Office Open XML: .docx/.xlsx/.pptx（ZIP 格式，PK 开头）
    if file_bytes[:2] == b"PK":
        return _clean_text(_extract_ooxml_text(file_bytes))

    # 旧版 Office .doc/.xls（OLE2 格式，D0 CF 11 E0 开头）
    if magic == b"\xd0\xcf\x11\xe0":
        return _clean_text(_extract_ole_text(file_bytes))

    # HTML 页面（多种开头）
    stripped = file_bytes[:16].lstrip()
    if stripped[:4] in (b"<htm", b"<!DO", b"<!do") or stripped[:4] in (b"<div", b"<p> ", b"\n<!-"):
        return _clean_text(_extract_html_text(file_bytes))

    # 纯文本（直接是中文 UTF-8 内容）
    try:
        text = file_bytes.decode("utf-8")
        if len(text) > 50:
            return _clean_text(text)
    except UnicodeDecodeError:
        pass

    raise ValueError(f"Unsupported file format, magic bytes: {file_bytes[:4]!r}")


def _extract_ooxml_text(file_bytes: bytes) -> str:
    """从 .docx（OOXML ZIP）中提取纯文本。"""
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception:
        pass
    # 降级：直接从 ZIP 里的 XML 提取文本节点
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            xml_content = ""
            for name in z.namelist():
                if name.endswith(".xml") and (
                    "word/document" in name or "content" in name.lower()
                ):
                    xml_content += z.read(name).decode("utf-8", errors="replace")
            text = re.sub(r"<[^>]+>", " ", xml_content)
            return re.sub(r"\s+", " ", text).strip()
    except Exception as e:
        raise ValueError(f"Cannot extract text from OOXML document: {e}")


def _extract_ole_text(file_bytes: bytes) -> str:
    """从旧版 .doc（OLE2）中提取纯文本，过滤非打印字符。"""
    try:
        import olefile
        with olefile.OleFileIO(io.BytesIO(file_bytes)) as ole:
            if ole.exists("WordDocument"):
                raw = ole.openstream("WordDocument").read()
                # 提取可打印的中文和ASCII字符
                text = raw.decode("utf-16-le", errors="replace")
                text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", text)
                text = re.sub(r"\s+", " ", text)
                return text.strip()
    except Exception:
        pass
    # 降级：暴力提取可读字符
    text = file_bytes.decode("utf-16-le", errors="replace")
    text = re.sub(r"[^\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\w\s，。！？；：""''（）【】]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class _HTMLTextExtractor(HTMLParser):
    SKIP_TAGS = {"script", "style", "head", "meta", "link"}

    def __init__(self):
        super().__init__()
        self._parts = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.SKIP_TAGS:
            self._skip = True

    def handle_endtag(self, tag):
        if tag.lower() in self.SKIP_TAGS:
            self._skip = False

    def handle_data(self, data):
        if not self._skip and data.strip():
            self._parts.append(data.strip())

    def get_text(self):
        return "\n".join(self._parts)


def _extract_html_text(file_bytes: bytes) -> str:
    """从 HTML 页面中提取正文文字，跳过 script/style。"""
    for enc in ("utf-8", "gbk", "gb2312"):
        try:
            html = file_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        html = file_bytes.decode("utf-8", errors="replace")
    parser = _HTMLTextExtractor()
    parser.feed(html)
    return parser.get_text()


def _clean_text(text: str) -> str:
    # Remove page numbers (standalone digits on a line)
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
    # Collapse 3+ consecutive blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip trailing whitespace per line
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return text.strip()


def prepare_text(text: str, doc_type: str) -> str:
    if doc_type in ("short", "medium"):
        return text

    # long: body-aware 三段采样
    # 中文年报/招股书前 8% 通常是封面/目录/免责声明，后 5% 是附录/签字页，均信息密度极低
    n = len(text)
    body_start = int(n * 0.08)   # 跳过前言/目录
    body_end   = int(n * 0.93)   # 跳过附录/签字
    body = text[body_start:body_end]
    blen = len(body)

    # 段1：正文前段（含关键披露/摘要，约8%-18%位置）
    seg1 = body[:2000]
    # 段2：正文核心（财务数据/核心条款集中区）
    seg2_s = blen // 2 - 1000
    seg2 = body[seg2_s: seg2_s + 2000]
    # 段3：正文后段（结论/风险/前瞻，约正文80%处，避开附录）
    seg3_s = int(blen * 0.80) - 1000
    seg3 = body[seg3_s: seg3_s + 2000]

    return (
        f"[节选·前段正文（已跳过封面目录）]\n{seg1}\n\n"
        f"[...省略...]\n\n"
        f"[节选·中段正文]\n{seg2}\n\n"
        f"[...省略...]\n\n"
        f"[节选·后段正文（已跳过附录签字页）]\n{seg3}"
    )
