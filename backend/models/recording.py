from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from core.database import Base


class Recording(Base):
    __tablename__ = "recordings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, index=True)
    recording_id = Column(String(255), unique=True, nullable=False)  # SignalWire recording ID
    url = Column(String(500))
    format = Column(String(10))  # mp3, wav, etc.
    stereo = Column(Boolean, default=False)
    direction = Column(String(20))  # both, inbound, outbound
    duration_seconds = Column(Integer)
    size_bytes = Column(Integer)
    state = Column(String(50))  # recording, completed, failed
    raw_data = Column(JSONB, default={})  # Store raw webhook data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    call = relationship("Call", back_populates="recordings")