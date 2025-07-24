from sqlalchemy import Column, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from core.database import Base


class AIInteraction(Base):
    __tablename__ = "ai_interactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, index=True)
    transcription_id = Column(UUID(as_uuid=True), ForeignKey("transcriptions.id"))
    prompt = Column(Text, nullable=False)
    response = Column(Text)
    vector_search_results = Column(JSON)
    relevance_score = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    call = relationship("Call", back_populates="ai_interactions")
    transcription = relationship("Transcription", back_populates="ai_interactions")