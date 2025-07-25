from sqlalchemy import Column, String, Text, Float, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from core.database import Base


class Transcription(Base):
    __tablename__ = "transcriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, index=True)
    speaker = Column(String(50))  # 'agent' or 'customer'
    text = Column(Text, nullable=False)
    confidence = Column(Float)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    sequence_number = Column(Integer)
    sentiment = Column(String(20), default='neutral')  # 'positive', 'neutral', 'negative'
    sentiment_score = Column(Float, default=0.5)  # 0.0 to 1.0
    raw_data = Column(JSONB, default={})  # Store raw webhook data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    call = relationship("Call", back_populates="transcriptions")
    ai_interactions = relationship("AIInteraction", back_populates="transcription")