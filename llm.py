import asyncio
import json
import re
import time

from openai import AsyncOpenAI

import config

SYSTEM_PROMPT = """你是A股金融公告分析专家，专注于半导体板块。
请分析公告文本，严格按JSON格式输出，不要输出任何其他内容，不要加```json标记。"""


def build_user_prompt(title: str, ann_type: str, text: str) -> str:
    return f"""公告标题：{title}
公告类型：{ann_type}

公告正文：
{text}

---
请完成以下分析，输出纯JSON：

{{
  "is_valuable": "有或无。判断标准——以下任意一类即为「有」：业绩变动（预增/预减/报告期财务数据）、股东增减持、股份回购、重大中标/合同签署、重组并购、股权变更、分红转增、重大诉讼/仲裁、监管处罚、产品/资质获批、定增/配股方案；仅包含以下内容判为「无」：董事监事换届、会计师续聘、股东大会通知、章程修订、日常资金授权、问询函格式性回复（无新增实质内容）",
  "summary": "is_valuable为有时：核心事件+关键数字+影响方向，50-100字；为无时填null",
  "reason": "一句话说明判断依据",
  "emotion": "is_valuable为有时填整数，标准如下（满足其一即可）；为无时填null。\n+2极度正面：重大重组/并购完成且战略意义显著；净利润/营收同比大幅增长(>100%)；重大产品获批或核心资质取得；大额股份回购完成且回购比例>3%。\n+1正面：业绩同比增长但幅度适中(10%-100%)；重大中标/签署合同且金额明确；定增/再融资方案获批且募资顺利；回购进展公告体现管理层信心。\n0中性：信息有实质内容但方向不明确；资产出售/转让但对整体影响有限；对外投资/设立子公司且规模较小；调研活动纪要无明确业绩指引。\n-1负面：业绩下滑同比下降但未亏损；募投项目进度延期且原因明确；重要股东减持计划披露；诉讼/仲裁立案且金额较小。\n-2极度负面：营收&净利润双降且由盈转亏；净利润同比暴跌(>-80%)或巨额亏损；重大违规/处罚涉及核心业务；重大诉讼败诉且赔偿金额巨大。",
  "granularity": "is_valuable为有时：整数0-100，衡量公告文本信息的具体程度与精确程度（信息细粒度），而非信息占比。为无时填null。\n评分维度（累加逻辑）：\n① 数值具体性：含精确数字（金额/比率/百分比）+20；仅定性描述+0。\n② 时间精度：精确到季度或具体日期+15；仅说「未来/近期」+0。\n③ 主体明确性：细化到业务线/产品/具体事件+10；仅说「公司整体」+5；完全模糊+0。\n④ 因果链完整性：有完整原因+传导路径+结论+15；仅有结论+0。\n⑤ 可证伪性：结论可被后续数据核实或证伪+10；无法检验+0。\n分值参考：「公司业绩良好」≈5；「净利润同比增长超预期」≈30；「Q3净利润12.3亿同比+28%」≈65；「Q3净利润12.3亿同比+28%超一致预期4.2%，因28nm产能利用率提升至92%带动毛利率+3.2pct」≈90。"
}}"""


def _make_client() -> AsyncOpenAI:
    if config.LLM_PROVIDER == "deepseek":
        return AsyncOpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
        )
    else:
        return AsyncOpenAI(
            api_key=config.QWEN_API_KEY,
            base_url=config.QWEN_BASE_URL,
        )


def _model_name() -> str:
    if config.LLM_PROVIDER == "deepseek":
        return config.DEEPSEEK_MODEL
    return config.QWEN_MODEL


def _parse_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Try to extract the first {...} block
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        return json.loads(match.group())
    raise ValueError(f"Cannot parse LLM response as JSON: {raw[:200]}")


async def call_llm(title: str, ann_type: str, text: str) -> tuple[dict, int, int]:
    client = _make_client()
    model = _model_name()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(title, ann_type, text)},
    ]

    last_err = None
    for attempt in range(config.MAX_RETRIES):
        try:
            t0 = time.monotonic()
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.1,
                ),
                timeout=config.LLM_TIMEOUT,
            )
            _ = time.monotonic() - t0
            raw = response.choices[0].message.content or ""
            result = _parse_json(raw)
            in_tok = response.usage.prompt_tokens if response.usage else 0
            out_tok = response.usage.completion_tokens if response.usage else 0
            return result, in_tok, out_tok
        except Exception as e:
            last_err = e
            # Exponential backoff
            wait = config.RETRY_DELAY * (2 ** attempt)
            await asyncio.sleep(wait)

    raise RuntimeError(f"LLM failed after {config.MAX_RETRIES} retries: {last_err}")
