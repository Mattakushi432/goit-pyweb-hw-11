from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator


class Settings(BaseSettings):
    """
    Класс для загрузки настроек из .env файла.
    """
    DATABASE_URL: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Создаем асинхронный "движок"
engine = create_async_engine(settings.DATABASE_URL)

# Создаем фабрику асинхронных сессий
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Базовый класс для наших моделей SQLAlchemy
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Зависимость (dependency) FastAPI для получения сессии базы данных.
    """
    async with AsyncSessionLocal() as session:
        yield session