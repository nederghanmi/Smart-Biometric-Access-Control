from __future__ import annotations

import json
import sqlite3
from datetime import datetime, date
from pathlib import Path
import csv

from config import LOG_DB_PATH


def _connect():
    conn = sqlite3.connect(LOG_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            user_id TEXT,
            event_date TEXT NOT NULL,
            event_time TEXT NOT NULL,
            status TEXT NOT NULL,
            confidence REAL,
            source TEXT DEFAULT 'camera',
            watermark TEXT
        )
        """
    )
    conn.commit()
    return conn


def add_log(user_name: str, status: str, confidence: float | None = None, user_id: str | None = None, source: str = "camera", watermark: str | None = None) -> None:
    now = datetime.now()
    conn = _connect()
    conn.execute(
        "INSERT INTO logs (user_name, user_id, event_date, event_time, status, confidence, source, watermark) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            user_name,
            user_id,
            now.strftime("%Y-%m-%d"),
            now.strftime("%H:%M:%S"),
            status,
            confidence,
            source,
            watermark,
        ),
    )
    conn.commit()
    conn.close()


def get_recent_logs(limit: int = 30):
    conn = _connect()
    rows = conn.execute(
        "SELECT user_name, event_date, event_time, status, confidence FROM logs ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def get_logs(status: str | None = None, limit: int = 100):
    conn = _connect()
    if status and status.upper() in {"AUTHORIZED", "REFUSED"}:
        rows = conn.execute(
            "SELECT user_name, event_date, event_time, status, confidence FROM logs WHERE status=? ORDER BY id DESC LIMIT ?",
            (status.upper(), limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT user_name, event_date, event_time, status, confidence FROM logs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return rows


def get_stats():
    conn = _connect()
    today = date.today().strftime("%Y-%m-%d")
    total_users = 0
    try:
        from reconnaissance import load_users

        total_users = len(load_users())
    except Exception:
        total_users = 0
    authorized = conn.execute(
        "SELECT COUNT(*) FROM logs WHERE status='AUTHORIZED' AND event_date=?",
        (today,),
    ).fetchone()[0]
    refused = conn.execute(
        "SELECT COUNT(*) FROM logs WHERE status='REFUSED' AND event_date=?",
        (today,),
    ).fetchone()[0]
    all_rows = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
    success_rate = 0.0
    if all_rows:
        approved = conn.execute("SELECT COUNT(*) FROM logs WHERE status='AUTHORIZED'").fetchone()[0]
        success_rate = round((approved / all_rows) * 100, 1)
    conn.close()
    return {
        "total_users": total_users,
        "authorized_today": authorized,
        "refused_today": refused,
        "success_rate": success_rate,
    }


def clear_logs():
    conn = _connect()
    conn.execute("DELETE FROM logs")
    conn.commit()
    conn.close()


def export_logs_csv(path: str | Path):
    rows = get_logs(limit=100000)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["User", "Date", "Time", "Status", "Confidence"])
        writer.writerows(rows)
