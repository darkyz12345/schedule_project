from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from config import DBSettings

db_settings = DBSettings()
DATABASE_URL = f'postgresql+asyncpg://{db_settings.USER_NAME}:{db_settings.PASSWORD}@{db_settings.HOST}:{db_settings.PORT}/{db_settings.DB_NAME}'
engine = create_async_engine(DATABASE_URL, echo=bool(db_settings.ECHO), poolclass=NullPool)
async_session_maker = async_sessionmaker(
    bind=engine, class_=AsyncSession,
    expire_on_commit=False
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session