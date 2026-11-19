from datetime import datetime, timedelta, timezone
import time
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # Issue time in milliseconds: a token issued before the account was
    # (re)created is rejected, so deleting and re-registering an email does
    # not revive old tokens.
    to_encode.update({"exp": expire, "iat_ms": int(time.time() * 1000)})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

def issued_before_account(payload: dict, created_at: datetime) -> bool:
    """True when the token predates the account it names (or has no issue time)."""
    issued = payload.get("iat_ms")
    if not isinstance(issued, int):
        return True
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return issued < int(created_at.timestamp() * 1000)
