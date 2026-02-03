"""
Database Configuration
生产级数据库引擎抽象 - 支持 SQLite (Dev) / PostgreSQL (Prod) 自动切换
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

from core.config import get_settings
from models.base import Base

logger = logging.getLogger(__name__)
settings = get_settings()


def _create_engine():
    """
    根据 DATABASE_URL 自动选择数据库引擎
    - sqlite: 使用 aiosqlite，NullPool（SQLite 不支持连接池）
    - postgresql: 使用 asyncpg，配置连接池
    """
    database_url = settings.DATABASE_URL

    if "sqlite" in database_url:
        logger.info("Using SQLite database (Development mode)")
        return create_async_engine(
            database_url,
            echo=settings.DEBUG,
            poolclass=NullPool,
            future=True,
        )
    elif "postgresql" in database_url:
        logger.info("Using PostgreSQL database (Production mode)")
        return create_async_engine(
            database_url,
            echo=settings.DEBUG,
            poolclass=AsyncAdaptedQueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            future=True,
        )
    else:
        raise ValueError(f"Unsupported database URL: {database_url}")


engine = _create_engine()

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（依赖注入）"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session_context() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话上下文（与get_db_session功能相同）"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """初始化数据库（创建表）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")


async def close_db() -> None:
    """关闭数据库连接"""
    await engine.dispose()
    logger.info("Database connection closed")


async def get_engine():
    """获取数据库引擎实例"""
    return engine
