import hashlib
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.infrastructure.persistence.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__ident="2b")

def verify_password(plain_password, hashed_password):
    if isinstance(plain_password, str):
        plain_password = plain_password.encode("utf-8")
    # If the password is longer than 72 bytes, bcrypt would fail or truncate.
    # We use SHA256 to ensure we always have a fixed-length input for bcrypt if it's too long.
    if len(plain_password) > 72:
        plain_password = hashlib.sha256(plain_password).hexdigest()
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    if isinstance(password, str):
        password = password.encode("utf-8")
    if len(password) > 72:
        password = hashlib.sha256(password).hexdigest()
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
