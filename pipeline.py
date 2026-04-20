import asyncio
import time

import pandas as pd
from tqdm import tqdm

import config
import db
import fetcher
import llm


def load_excel_to_db():
    print(f"正在读取 {config.INPUT_EXCEL} ...")
    df = pd.read_excel(config.INPUT_EXCEL, sheet_name="Sheet1", dtype=str)
    df = df.fillna("")
    records = df.rename(columns={
        "股票代码": "股票代码",
        "发布时间": "发布时间",
        "公告标题": "公告标题",
        "公告类型": "公告类型",
        "公告链接": "公告链接",
    }).to_dict("records")
    db.create_tables()
    db.bulk_insert(records)
    stats = db.get_stats()
    print(f"数据库就绪：总计 {stats.get('total', 0)} 条，待处理 {stats.get('pending', 0)} 条")


def _doc_type(length: int) -> str:
    if length < config.SHORT_THRESHOLD:
        return "short"
    if length <= config.LONG_THRESHOLD:
        return "medium"
    return "long"


async def process_one(record: dict, semaphore: asyncio.Semaphore, counters: dict, pbar: tqdm):
    async with semaphore:
        rid = record["id"]
        title = record.get("公告标题", "")
        ann_type = record.get("公告类型", "")
        url = record.get("公告链接", "")

        try:
            # --- Fetch PDF ---
            text, fetch_time = await fetcher.fetch_pdf(url)
            text_len = len(text)
            dtype = _doc_type(text_len)
            db.update_fetched(rid, text, text_len, dtype, fetch_time)

            # --- Prepare text for LLM ---
            prepared = fetcher.prepare_text(text, dtype)

            # --- Call LLM ---
            t0 = time.monotonic()
            result, in_tok, out_tok = await llm.call_llm(title, ann_type, prepared)
            llm_time = time.monotonic() - t0

            is_valuable = result.get("is_valuable", "无")
            summary = result.get("summary")
            reason = result.get("reason", "")
            emotion = result.get("emotion")

            db.update_done(rid, is_valuable, summary, reason, emotion, llm_time, in_tok, out_tok)

            counters["done"] += 1
            counters["in_tok"] += in_tok
            counters["out_tok"] += out_tok
            if is_valuable == "有":
                counters["valuable"] += 1
            else:
                counters["not_valuable"] += 1

        except Exception as e:
            err_str = str(e)
            db.update_failed(rid, f"{type(e).__name__}: {err_str}" if err_str else type(e).__name__)
            counters["failed"] += 1
        finally:
            pbar.update(1)
            counters["processed"] += 1
            _maybe_print_stats(counters)


def _maybe_print_stats(counters: dict):
    if counters["processed"] % 100 == 0:
        in_tok = counters["in_tok"]
        out_tok = counters["out_tok"]
        # DeepSeek pricing: input ¥0.001/1K, output ¥0.002/1K
        cost = (in_tok / 1000 * 0.001) + (out_tok / 1000 * 0.002)
        total_tok = in_tok + out_tok
        print(
            f"\n  [统计] 有价值:{counters['valuable']} 无价值:{counters['not_valuable']} "
            f"| Token消耗:{total_tok:,} | 预估费用:¥{cost:.2f}"
        )


async def run_pipeline():
    load_excel_to_db()

    records = db.get_pending() + db.get_retryable()
    total = len(records)
    if total == 0:
        print("没有待处理记录，流水线退出。")
        return

    print(f"共 {total} 条记录待处理，并发数={config.CONCURRENCY}")

    semaphore = asyncio.Semaphore(config.CONCURRENCY)
    counters = {
        "done": 0, "failed": 0, "processed": 0,
        "valuable": 0, "not_valuable": 0,
        "in_tok": 0, "out_tok": 0,
    }

    with tqdm(
        total=total,
        desc="处理进度",
        unit="条",
        dynamic_ncols=True,
    ) as pbar:
        tasks = [process_one(r, semaphore, counters, pbar) for r in records]
        await asyncio.gather(*tasks, return_exceptions=True)

    in_tok = counters["in_tok"]
    out_tok = counters["out_tok"]
    cost = (in_tok / 1000 * 0.001) + (out_tok / 1000 * 0.002)
    print(
        f"\n流水线完成：成功={counters['done']} 失败={counters['failed']}"
        f" | Token总消耗={in_tok + out_tok:,} | 预估总费用:¥{cost:.2f}"
    )
