"""
Sets up a SQLite database for user accounts.
SQLite stores everything in a single file (users.db) — no separate
database server needed, perfect for a project like this.
"""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().with_name("users.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name, e.g. row["username"]
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS task_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            username TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            task_type TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            state TEXT,
            stderr TEXT,
            execution_time_sec REAL,
            client_id TEXT,
            language TEXT,
            payload TEXT,
            stdout TEXT,
            worker TEXT,
            result_json TEXT,
            completed_at TEXT
        )
    """)

    # Add columns to databases created by earlier project versions.
    existing_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(task_logs)").fetchall()
    }
    new_columns = {
        "client_id": "TEXT",
        "language": "TEXT",
        "payload": "TEXT",
        "stdout": "TEXT",
        "worker": "TEXT",
        "result_json": "TEXT",
        "completed_at": "TEXT",
    }
    for column, column_type in new_columns.items():
        if column not in existing_columns:
            try:
                conn.execute(f"ALTER TABLE task_logs ADD COLUMN {column} {column_type}")
            except sqlite3.OperationalError as exc:
                # The API and workers may start together and race on the same
                # additive migration. A concurrent migration is harmless.
                if "duplicate column name" not in str(exc).lower():
                    raise

    conn.commit()
    conn.close()


def save_task_result(task_id: str, state: str, result, worker: str | None = None):
    """Persist a completed task result beyond Celery's Redis retention window."""
    if isinstance(result, dict):
        result_data = result
    else:
        result_data = {
            "status": "error",
            "stdout": "",
            "stderr": str(result),
        }

    worker_name = result_data.get("worker") or worker
    conn = get_connection()
    if worker_name is None:
        existing = conn.execute(
            "SELECT worker FROM task_logs WHERE task_id = ?", (task_id,)
        ).fetchone()
        worker_name = existing["worker"] if existing else None
    if worker_name:
        result_data = {**result_data, "worker": worker_name}

    conn.execute(
        """UPDATE task_logs
           SET state = ?, stdout = ?, stderr = ?, execution_time_sec = ?,
               worker = COALESCE(?, worker), result_json = ?,
               completed_at = COALESCE(completed_at, ?)
           WHERE task_id = ?""",
        (
            state,
            result_data.get("stdout", ""),
            result_data.get("stderr", ""),
            result_data.get("execution_time_sec"),
            worker_name,
            json.dumps(result_data, ensure_ascii=False, default=str),
            datetime.now(timezone.utc).isoformat(),
            task_id,
        ),
    )
    conn.commit()
    conn.close()
    return result_data


def task_result_from_row(task: dict):
    """Load a saved result, or build the fields available in older records."""
    if task.get("result_json"):
        return json.loads(task["result_json"])
    if task.get("state") in (None, "PENDING"):
        return None
    return {
        "status": "success" if task["state"] == "SUCCESS" else "error",
        "stdout": task.get("stdout") or "",
        "stderr": task.get("stderr") or "",
        "execution_time_sec": task.get("execution_time_sec"),
        "worker": task.get("worker"),
    }


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
