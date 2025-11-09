# data/db.py
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Iterable, List, Tuple, Optional, Dict, Any

# --- Config ---
# You can override with env var SMARTSAVER_DB=/absolute/path/to/file.db
DB_PATH = Path(os.getenv("SMARTSAVER_DB", "./smartsavernet.db")).resolve()


def get_conn() -> sqlite3.Connection:
    """
    Return a SQLite connection with sensible defaults for a small app.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Helpful pragmas for small apps; adjust if you need WAL or stricter journaling.
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    """
    Create the minimal schema SmartSaverNet needs right now.
    """
    cur = conn.cursor()

    # Basic meta table (optional but handy)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )

    # Core transactions table used by the UI:
    # - date: ISO string 'YYYY-MM-DD'
    # - amount: positive for spend, negative for refunds/credits (or flip if you prefer)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT
        );
        """
    )

    # Helpful indices
    cur.execute("CREATE INDEX IF NOT EXISTS idx_txn_user_date ON transactions(user_id, date DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_txn_category ON transactions(category);")

    conn.commit()


# --- CRUD helpers for transactions ---

def add_transaction(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    date: str,
    description: str,
    amount: float,
    category: Optional[str] = None,
) -> int:
    """
    Insert a single transaction. Returns inserted row id.
    """
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO transactions (user_id, date, description, amount, category)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, date, description, amount, category),
    )
    conn.commit()
    return int(cur.lastrowid)


def bulk_insert_transactions(
    conn: sqlite3.Connection,
    rows: Iterable[Tuple[str, str, str, float, Optional[str]]],
) -> int:
    """
    Bulk insert transactions. Expects tuples of (user_id, date, description, amount, category).
    Returns number of inserted rows.
    """
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT INTO transactions (user_id, date, description, amount, category)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return cur.rowcount or 0


def fetch_recent_transactions(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    limit: int = 50,
) -> List[sqlite3.Row]:
    """
    Return recent transactions for a user, newest first.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT date, description, amount, category
        FROM transactions
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        LIMIT ?
        """,
        (user_id, limit),
    )
    return cur.fetchall()


def totals_by_category(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    date_from: Optional[str] = None,  # 'YYYY-MM-DD'
    date_to: Optional[str] = None,    # 'YYYY-MM-DD'
) -> List[sqlite3.Row]:
    """
    Aggregate spend by category over an optional date range.
    """
    params: List[Any] = [user_id]
    where = ["user_id = ?"]

    if date_from:
        where.append("date >= ?")
        params.append(date_from)
    if date_to:
        where.append("date <= ?")
        params.append(date_to)

    sql = f"""
        SELECT COALESCE(category, 'Uncategorized') AS category,
               SUM(amount) AS total
        FROM transactions
        WHERE {' AND '.join(where)}
        GROUP BY COALESCE(category, 'Uncategorized')
        ORDER BY total DESC
    """
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur.fetchall()


def monthly_spend_summary(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    year: int,
    month: int,
) -> Dict[str, Any]:
    """
    Quick monthly summary: total spend and count of transactions.
    """
    # Build YYYY-MM prefix and next month prefix for range filter
    from datetime import date
    if month == 12:
        next_y, next_m = year + 1, 1
    else:
        next_y, next_m = year, month + 1
    start = f"{year:04d}-{month:02d}-01"
    end = f"{next_y:04d}-{next_m:02d}-01"

    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS n, COALESCE(SUM(amount), 0) AS total
        FROM transactions
        WHERE user_id = ?
          AND date >= ?
          AND date < ?
        """,
        (user_id, start, end),
    )
    row = cur.fetchone()
    return {"year": year, "month": month, "txns": row["n"], "total": row["total"]}


# --- Utilities ---

def reset_db() -> None:
    """
    Danger: deletes the DB file. Useful for local resets.
    """
    if DB_PATH.exists():
        DB_PATH.unlink()
