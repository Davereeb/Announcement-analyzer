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
  "emotion": "is_valuable为有时填整数，标准如下；为无时填null。\n+2极度正面：净利润/营收同比增长>100%，或重大并购重组完成且具战略意义，或核心产品/资质重大获批，或大额回购完成(>3%股本)。\n+1正面：业绩同比增长10%-100%，或重大中标/签约金额明确，或定增再融资方案获批，或回购进展体现管理层信心。\n0中性：含实质信息但方向不明确，或小额投资/设立子公司，或战略合作但金额未披露，或调研纪要无明确业绩指引。\n-1负面：业绩下滑但未亏损，或募投项目延期，或重要股东减持计划披露，或小额诉讼仲裁立案。\n-2极度负面：由盈转亏或净利润同比暴跌>80%，或营收净利润双降且幅度显著，或重大违规处罚涉及核心业务，或重大诉讼败诉赔偿巨大。",
  "granularity": "整数0-100，估算全文中「对股价判断有直接参考价值的内容」占全文字数的百分比。评估标准：关键财务数据/金额/比率/事件结论=高价值；背景介绍/历史沿革/法律条文引用/模板声明=低价值。示例：纯财务摘要≈80，季报全文≈25，章程≈3，重组报告书≈35。长文本若仅能看到节选片段，基于所见内容估算整体密度。"
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
