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
  "is_valuable": "有或无（是否包含影响股价的实质信息：业绩变动、增减持、回购、中标、重组并购、股权变更、分红、重大诉讼、处罚、重大合同、产品获批等）",
  "summary": "有价值时：核心事件+关键数据+影响方向，50-100字；无价值时填null",
  "reason": "一句话说明判断依据",
  "emotion": "有价值时给整数：2极度正面/1正面/0中性/(-1)负面/(-2)极度负面；无价值时填null"
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
