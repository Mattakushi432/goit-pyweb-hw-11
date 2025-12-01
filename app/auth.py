from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
from passlib.context import CryptContext

import redis.asyncio as redis
import pickle
from app.config import settings

from app.database import get_db
from app.models import User
import app.crud as crud


class Settings(BaseSettings):
    """
    Завантажує секрети з .env для auth.
    """
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class AuthService:

    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=1,
            decode_responses=False
        )

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Перевіряє, чи збігається пароль з хешем."""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Створює хеш пароля."""
        return pwd_context.hash(password)

    def create_email_token(self, data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=7)
        to_encode.update({"iat": datetime.utcnow(), "exp": expire})
        # Використовуємо SECRET_KEY та ALGORITHM з settings
        token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return token

    async def get_email_from_token(self, token: str):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            email = payload.get("sub")
            return email
        except JWTError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid token")

    async def create_token(self, data: dict, expires_delta: timedelta) -> str:
        """Створює JWT токен (access або refresh)."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        return encoded_jwt

    async def create_reset_token(self, data: dict) -> str:
        """Створює короткочасний JWT токен для скидання паролю (наприклад, 1 година)."""
        to_encode = data.copy()
        # Токен діє 1 годину (3600 секунд)
        expire = datetime.now(timezone.utc) + timedelta(hours=1)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        return encoded_jwt

    async def create_access_token(self, data: dict) -> str:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return await self.create_token(data, expires_delta)

    async def create_refresh_token(self, data: dict) -> str:
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        return await self.create_token(data, expires_delta)

    async def decode_token(self, token: str) -> Optional[str]:
        """
        Декодує токен (access або refresh) та повертає email.
        """
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            email: str = payload.get("sub")
            if email is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials"
                )
            return email
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )

    async def get_current_user(
            self, token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
    ) -> User:
        """
        Залежність для FastAPI. Отримує токен, перевіряє його та повертає об'єкт User.
        Використовує Redis для кешування користувача.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        email = await self.decode_token(token)
        if email is None:
            raise credentials_exception

        user_key = f"user:{email}"
        user_cache = await self.redis_client.get(user_key)

        if user_cache:
            user = pickle.loads(user_cache)
            if user:
                return user

        user = await crud.get_user_by_email(db, email=email)

        if user is None:
            raise credentials_exception

        await self.redis_client.set(user_key, pickle.dumps(user), ex=900)

        return user


auth_service = AuthService()
