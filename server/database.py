"""
Sets up a SQLite database for user accounts.
SQLite stores everything in a single file (users.db) — no separate
database server needed, perfect for a project like this.
"""

import sqlite3

DB_PATH = "users.db"


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
            execution_time_sec REAL
        )
    """)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")