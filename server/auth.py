"""
Handles JWT token creation and verification.
"""

import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jose import JWTError, jwt
from passlib.context import CryptContext

def _load_secret_key() -> str:
    configured_key = os.environ.get("OFFLOAD_SECRET_KEY", "").strip()
    if configured_key:
        if len(configured_key) < 32:
            raise RuntimeError("OFFLOAD_SECRET_KEY must be at least 32 characters")
        return configured_key

    key_path = Path(__file__).with_name(".secret_key")
    for _ in range(20):
        try:
            key_fd = os.open(key_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            try:
                local_key = key_path.read_text(encoding="utf-8").strip()
            except FileNotFoundError:
                time.sleep(0.05)
                continue
            if len(local_key) >= 32:
                return local_key
            if local_key:
                raise RuntimeError(f"The local JWT key at {key_path} is invalid")
            time.sleep(0.05)
        except OSError as exc:
            raise RuntimeError(
                "Could not create the local JWT key; set OFFLOAD_SECRET_KEY instead"
            ) from exc
        else:
            local_key = secrets.token_urlsafe(48)
            with os.fdopen(key_fd, "w", encoding="utf-8") as key_file:
                key_file.write(local_key + "\n")
            return local_key

    raise RuntimeError("Could not read the local JWT key; set OFFLOAD_SECRET_KEY instead")


SECRET_KEY = _load_secret_key()
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Returns the username if valid, None if invalid/expired."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
