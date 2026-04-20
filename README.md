# A股公告情感分析系统

自动批量下载、解析 A 股上市公司公告（PDF / Word / HTML），调用大语言模型（DeepSeek / Qwen）完成三项核心任务：

1. **价值判断** — 判断公告是否含有影响股价的实质信息
2. **核心摘要** — 生成 50-100 字的精炼摘要
3. **情感评分** — 给出 -2（极度负面）到 +2（极度正面）的量化评分

结果存入 SQLite 数据库，并导出带颜色格式的 Excel 报告。支持**断点续跑**：中途停止后重新运行，自动跳过已完成记录。

---

## 目录结构

```
announcement_analyzer/
├── config.py            # 配置文件（含API Key，本地保存，不上传）
├── config.example.py    # 配置模板（复制后重命名为 config.py）
├── main.py              # 一键启动入口
├── pipeline.py          # 异步流水线主逻辑
├── fetcher.py           # PDF/文档下载与文本提取
├── llm.py               # LLM调用封装（DeepSeek / Qwen）
├── db.py                # SQLite数据库操作层
├── exporter.py          # Excel导出（条件颜色格式）
├── generate_reports.py  # 生成PDF工作日志与结果总结
└── requirements.txt     # Python依赖列表
```

---

## 环境要求

- Python 3.10 或更高版本
- Node.js（用于绕过东方财富网站的反爬虫验证，需可在终端执行 `node` 命令）

验证方法：
```bash
python3 --version   # 应输出 Python 3.10+
node --version      # 应输出 v14+ 以上版本
```

---

## 快速开始

### 第一步：克隆项目

```bash
git clone https://github.com/你的用户名/announcement_analyzer.git
cd announcement_analyzer
```

### 第二步：安装依赖

```bash
pip install -r requirements.txt
```

### 第三步：配置 API Key

将 `config.example.py` 复制一份，重命名为 `config.py`：

```bash
cp config.example.py config.py
```

然后用任意文本编辑器打开 `config.py`，填入以下内容：

| 配置项 | 说明 |
|--------|------|
| `INPUT_EXCEL` | 输入Excel文件名（放在项目根目录） |
| `DEEPSEEK_API_KEY` | DeepSeek API Key，申请地址：https://platform.deepseek.com/ |
| `QWEN_API_KEY` | Qwen API Key（备用），申请地址：https://dashscope.aliyuncs.com/ |
| `LLM_PROVIDER` | 选择使用哪个模型：`"deepseek"` 或 `"qwen"` |
| `CONCURRENCY` | 并发数，默认20，如遇限流可调低至10 |

### 第四步：准备输入文件

将包含公告数据的 Excel 文件放入项目根目录，文件需包含以下列：

| 列名 | 说明 |
|------|------|
| 股票代码 | 如 `300666` |
| 发布时间 | 如 `2024-01-15` |
| 公告标题 | 如 `江丰电子:关于xxx的公告` |
| 公告类型 | 如 `业绩预告` |
| 公告链接 | 东方财富PDF直链，如 `http://pdf.dfcfw.com/pdf/...` |

然后在 `config.py` 中将 `INPUT_EXCEL` 改为你的文件名。

### 第五步：运行

```bash
python3 main.py
```

程序会显示实时进度条，每处理 100 条打印一次统计信息（有价值数量、Token 消耗、预估费用）。

**中断后续跑：** 直接再次运行 `python3 main.py`，已完成的记录会自动跳过。

---

## 输出文件

| 文件 | 说明 |
|------|------|
| `announcements.db` | SQLite数据库，存储全量处理结果和原始文本 |
| `results_YYYYMMDD_HHMMSS.xlsx` | 带格式的Excel结果报告 |

### Excel 输出列说明

| 列名 | 说明 |
|------|------|
| 股票代码 / 股票名称 | 来自输入数据 |
| 发布时间 / 公告标题 / 公告类型 | 来自输入数据 |
| is_valuable | `有` 或 `无`，是否含有价值信息 |
| summary | LLM生成的50-100字摘要 |
| reason | LLM判断理由 |
| emotion | 情感评分（-2 ~ +2） |
| doc_type | 文档类型（short / medium / long） |
| fetch_time / llm_time | 各阶段耗时（秒） |

### 情感评分颜色说明

| 颜色 | 评分 | 含义 |
|------|------|------|
| 🟢 深绿 | +2 | 极度正面 |
| 🟢 浅绿 | +1 | 正面 |
| ⬜ 白色 | 0 | 中性 |
| 🔴 浅红 | -1 | 负面 |
| 🔴 深红 | -2 | 极度负面 |

---

## 生成PDF报告（可选）

处理完成后，可运行以下命令生成中英文工作日志和结果总结（共4个PDF）：

```bash
python3 generate_reports.py
```

---

## 支持的文件格式

系统自动识别公告链接返回的文件类型，无需手动配置：

| 格式 | 处理方式 |
|------|----------|
| PDF (`.pdf`) | pdfplumber 提取 |
| Word文档 (`.docx`) | python-docx + XML 降级解析 |
| 旧版Word (`.doc`) | olefile 二进制解析 |
| HTML页面 | html.parser 过滤标签提取正文 |
| 纯文本 (UTF-8) | 直接 decode |

---

## 费用估算参考

以 DeepSeek `deepseek-chat` 模型为例，处理17,000条公告的实际消耗：

| 项目 | 数值 |
|------|------|
| 输入 Token | 约 3600 万 |
| 输出 Token | 约 140 万 |
| 总费用 | 约 ¥39（约合 $5.5 USD） |

---

## 常见问题

**Q: 运行时报错 `node: command not found`**
A: 需要安装 Node.js。macOS 可用 `brew install node`，或前往 https://nodejs.org 下载安装。

**Q: 遇到 `402 Insufficient Balance` 错误**
A: DeepSeek 账户余额不足，充值后直接重新运行 `python3 main.py`，会自动从中断处继续，不会重复计费。

**Q: 部分记录一直失败怎么办**
A: 查看 `announcements.db` 中的 `error_msg` 字段了解失败原因。网络超时类错误可重新运行重试；`Unsupported file format` 表示该公告为不支持的格式（如 RAR 压缩包），需手动处理。

**Q: 如何只处理特定股票**
A: 在输入 Excel 中只保留目标股票的行，然后运行即可。如果数据库已有其他记录，新记录会自动追加而不影响旧记录。

---

## 技术栈

- **异步并发**：`asyncio` + `asyncio.Semaphore`（20并发）
- **HTTP客户端**：`httpx`（流式下载，支持大文件）
- **PDF解析**：`pdfplumber`
- **Word解析**：`python-docx`、`olefile`
- **LLM调用**：`openai` SDK（兼容 DeepSeek / Qwen 接口）
- **数据存储**：`sqlite3`（标准库）
- **Excel导出**：`openpyxl`
- **进度显示**：`tqdm`

---

## License

MIT
