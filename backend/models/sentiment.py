from sqlalchemy import Column, String, DateTime, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from core.database import Base


class SentimentHistory(Base):
    __tablename__ = "sentiment_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id"), nullable=False, index=True)
    sentiment = Column(String(20), nullable=False)  # happy, neutral, mad
    confidence = Column(Float, nullable=False)
    transcription_context = Column(String)  # Last few transcriptions used for analysis
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    call = relationship("Call", back_populates="sentiment_history")