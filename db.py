import sqlite3
import config


def _conn():
    return sqlite3.connect(config.OUTPUT_DB)


def create_tables():
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS announcements (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                股票代码         TEXT,
                发布时间         TEXT,
                公告标题         TEXT,
                公告类型         TEXT,
                公告链接         TEXT UNIQUE,

                status          TEXT DEFAULT 'pending',

                text_length     INTEGER,
                doc_type        TEXT,

                is_valuable     TEXT,
                summary         TEXT,
                reason          TEXT,
                emotion         INTEGER,
                granularity     INTEGER,

                fetch_time      REAL,
                llm_time        REAL,
                input_tokens    INTEGER,
                output_tokens   INTEGER,
                retry_count     INTEGER DEFAULT 0,
                error_msg       TEXT,
                processed_at    TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_status ON announcements(status);
            CREATE INDEX IF NOT EXISTS idx_stock  ON announcements(股票代码);
        """)


def bulk_insert(records: list[dict]):
    sql = """
        INSERT OR IGNORE INTO announcements (股票代码, 发布时间, 公告标题, 公告类型, 公告链接)
        VALUES (:股票代码, :发布时间, :公告标题, :公告类型, :公告链接)
    """
    with _conn() as conn:
        conn.executemany(sql, records)
    return


def get_pending(limit: int = 0) -> list[dict]:
    sql = "SELECT * FROM announcements WHERE status='pending'"
    if limit:
        sql += f" LIMIT {limit}"
    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql).fetchall()
    return [dict(r) for r in rows]


def update_fetched(id: int, text: str, text_length: int, doc_type: str, fetch_time: float):
    with _conn() as conn:
        conn.execute(
            """UPDATE announcements
               SET status='fetched', text_length=?, doc_type=?, fetch_time=?
               WHERE id=?""",
            (text_length, doc_type, fetch_time, id),
        )
    # Store text separately to keep the main record slim; reuse error_msg col as temp storage
    # Actually store in a separate text store via a blob approach — use a side table
    _store_text(id, text)


def _store_text(id: int, text: str):
    with _conn() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS announcement_texts (id INTEGER PRIMARY KEY, text TEXT)"
        )
        conn.execute(
            "INSERT OR REPLACE INTO announcement_texts (id, text) VALUES (?, ?)",
            (id, text),
        )


def get_text(id: int) -> str:
    with _conn() as conn:
        row = conn.execute(
            "SELECT text FROM announcement_texts WHERE id=?", (id,)
        ).fetchone()
    return row[0] if row else ""


def update_done(
    id: int,
    is_valuable: str,
    summary: str,
    reason: str,
    emotion,
    granularity,
    llm_time: float,
    input_tokens: int,
    output_tokens: int,
):
    from datetime import datetime
    with _conn() as conn:
        conn.execute(
            """UPDATE announcements
               SET status='done', is_valuable=?, summary=?, reason=?, emotion=?,
                   granularity=?, llm_time=?, input_tokens=?, output_tokens=?,
                   processed_at=?, error_msg=NULL
               WHERE id=?""",
            (
                is_valuable, summary, reason, emotion,
                granularity, llm_time, input_tokens, output_tokens,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                id,
            ),
        )


def update_failed(id: int, error_msg: str):
    with _conn() as conn:
        conn.execute(
            """UPDATE announcements
               SET status='failed', error_msg=?, retry_count=retry_count+1
               WHERE id=?""",
            (error_msg, id),
        )


def get_stats() -> dict:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) FROM announcements GROUP BY status"
        ).fetchall()
    stats = {r[0]: r[1] for r in rows}
    total = sum(stats.values())
    stats["total"] = total
    return stats


def get_retryable() -> list[dict]:
    sql = f"SELECT * FROM announcements WHERE status='failed' AND retry_count < {config.MAX_RETRIES}"
    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql).fetchall()
    return [dict(r) for r in rows]
