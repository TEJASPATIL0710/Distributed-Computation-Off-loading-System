"""
Run this to add a new authorized user. Only you (the project owner)
should run this — there's no public "sign up" page, matching a
real internal-tool pattern where an admin provisions accounts.

Usage: python create_user.py <username> <password>
"""

import sys
from datetime import datetime, timezone

from passlib.context import CryptContext

from database import get_connection, init_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_user(username: str, password: str):
    init_db()
    conn = get_connection()
    password_hash = pwd_context.hash(password)
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, password_hash, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        print(f"User '{username}' created.")
    except Exception as e:
        print(f"Failed to create user: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python create_user.py <username> <password>")
        sys.exit(1)
    create_user(sys.argv[1], sys.argv[2])