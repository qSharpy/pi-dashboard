import os
import bcrypt
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import Cookie, HTTPException, status

JWT_SECRET = os.getenv("JWT_SECRET", "changeme")
PASSWORD_HASH = os.getenv("PASSWORD_HASH", "")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7


def verify_password(password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), PASSWORD_HASH.encode())
    except Exception:
        return False


def create_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    return jwt.encode({"exp": expire, "sub": "admin"}, JWT_SECRET, algorithm=ALGORITHM)


def verify_token(token: str | None) -> bool:
    if not token:
        return False
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return True
    except JWTError:
        return False


def require_auth(session: str | None = Cookie(default=None)):
    if not verify_token(session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
