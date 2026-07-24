from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from datetime import UTC, datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Boolean, Column, Enum, StaticPool, String, DateTime, Text
from app.core.config import settings
from sqlalchemy.sql import func
from app.core.database import Base

class ResourceDB(Base):
    __tablename__ = "resources"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    resource_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))