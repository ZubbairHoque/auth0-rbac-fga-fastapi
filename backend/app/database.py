from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Boolean, Column, String, DateTime, Text
from app.config import settings
from sqlalchemy.sql import func

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL queries in debug mode
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    """Base class for all database models."""
    pass

# SQLAlchemy Models
class ResourceDB(Base):
    __tablename__ = "resources"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    resource_type = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class InvitationDB(Base):
    __tablename__ = "Invitations"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True)
    role = Column(String)
    token = Column(String)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

# Database dependency
async def get_db():
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Database initialization
async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
