from datetime import UTC, datetime
from sqlalchemy import Column, String, DateTime, Text
from app.core.database import Base

class ResourceDB(Base):
    __tablename__ = "resources"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    resource_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))