from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, JSON, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from core.database import Base


class CallSummary(Base):
    __tablename__ = "call_summaries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    key_topics = Column(ARRAY(Text))
    sentiment_score = Column(Float)
    action_items = Column(JSON)
    meta_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    call = relationship("Call", back_populates="summary")


class CallDocumentReference(Base):
    __tablename__ = "call_document_references"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(String(255))
    document_title = Column(Text)
    relevance_score = Column(Float)
    accessed_at = Column(DateTime(timezone=True), server_default=func.now())
    context = Column(Text)
    
    # Relationships
    call = relationship("Call", back_populates="document_references")