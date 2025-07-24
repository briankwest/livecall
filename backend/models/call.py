from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from core.database import Base


class CallStatus(str, enum.Enum):
    ACTIVE = "active"
    ENDED = "ended"
    FAILED = "failed"


class ListeningMode(str, enum.Enum):
    AGENT = "agent"
    CUSTOMER = "customer"
    BOTH = "both"


class Call(Base):
    __tablename__ = "calls"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    signalwire_call_id = Column(String(255), unique=True, nullable=False, index=True)
    phone_number = Column(String(50))
    agent_id = Column(String(255))
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    status = Column(String(50), default="active", index=True)
    listening_mode = Column(String(20), default="both")
    raw_data = Column(JSONB, default={})  # Store raw webhook data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    transcriptions = relationship("Transcription", back_populates="call", cascade="all, delete-orphan")
    ai_interactions = relationship("AIInteraction", back_populates="call", cascade="all, delete-orphan")
    summary = relationship("CallSummary", back_populates="call", uselist=False, cascade="all, delete-orphan")
    document_references = relationship("CallDocumentReference", back_populates="call", cascade="all, delete-orphan")
    recordings = relationship("Recording", back_populates="call", cascade="all, delete-orphan")