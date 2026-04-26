"""Database session management - SQLite-safe with optional PostgreSQL async support."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from core.config import get_settings

settings = get_settings()

_is_sqlite = settings.database_url.startswith("sqlite")

# ═══════════════════════════════════════════════════════════════════════════════
# SYNC ENGINE - works for both SQLite (dev) and PostgreSQL (prod)
# ═══════════════════════════════════════════════════════════════════════════════
if _is_sqlite:
    # SQLite needs special handling - no real connection pooling
    engine = create_engine(
        settings.database_url,
        echo=settings.database_echo,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # PostgreSQL/MySQL with full connection pooling
    engine = create_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_pre_ping=True,
        pool_size=20,
        max_overflow=40,
        pool_recycle=3600,
        pool_timeout=30,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ═══════════════════════════════════════════════════════════════════════════════
# ASYNC ENGINE - only enabled for PostgreSQL (asyncpg required)
# ═══════════════════════════════════════════════════════════════════════════════
async_engine = None
AsyncSessionLocal = None

if settings.database_url.startswith("postgresql://") or settings.database_url.startswith("postgresql+asyncpg://"):
    try:
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        
        _async_url = settings.database_url
        if _async_url.startswith("postgresql://"):
            _async_url = _async_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        async_engine = create_async_engine(
            _async_url,
            echo=settings.database_echo,
            pool_pre_ping=True,
            pool_size=30,
            max_overflow=50,
            pool_recycle=3600,
            pool_timeout=10,
        )
        
        AsyncSessionLocal = async_sessionmaker(
            async_engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    except ImportError:
        # asyncpg not installed - fall back to sync only
        pass

Base = declarative_base()


def get_db():
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    """Async database dependency. Falls back to sync if async not available."""
    if AsyncSessionLocal is not None:
        async with AsyncSessionLocal() as session:
            yield session
    else:
        # Fallback to sync session for SQLite
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
