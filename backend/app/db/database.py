import os
import logging
from typing import AsyncGenerator
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# Load .env so DATABASE_URL is available regardless of import order
load_dotenv()

logger = logging.getLogger("uvicorn")

# Read DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Please configure DATABASE_URL in backend/.env"
    )

# SQLAlchemy 2.x async engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Async session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for future SQLAlchemy declarative models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session.
    Session is automatically closed when the request completes.
    """
    async with async_session_factory() as session:
        yield session


async def verify_db_connection() -> bool:
    """
    Verify database connectivity with a simple SELECT 1.
    Does not create tables or modify database state.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified successfully (SELECT 1).")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise
