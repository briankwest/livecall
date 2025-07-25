import logging
from typing import Tuple, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select
import json

from models import Call, Transcription, SentimentHistory
from services.openai_service import OpenAIService
from core.config import settings

logger = logging.getLogger(__name__)


class SentimentAnalysisService:
    """Service for analyzing call sentiment using GPT-4o-mini"""
    
    def __init__(self):
        self.openai_service = OpenAIService()
        
    async def analyze_sentiment(self, transcriptions: List[Transcription]) -> Tuple[str, float]:
        """
        Analyze sentiment from recent transcriptions
        Returns: (sentiment, confidence) where sentiment is 'happy', 'neutral', or 'mad'
        """
        if not transcriptions:
            return "neutral", 0.0
            
        # Build conversation context
        conversation = []
        for t in transcriptions:
            conversation.append(f"{t.speaker.upper()}: {t.text}")
        
        conversation_text = "\n".join(conversation)
        
        # Use GPT-4o-mini for sentiment analysis
        system_prompt = """You are a sentiment analysis assistant. Analyze the following conversation and determine the overall sentiment.
        
        Classify the sentiment as one of: happy, neutral, or mad
        
        Consider:
        - Tone and language used
        - Customer satisfaction indicators
        - Frustration or anger signals
        - Positive or appreciative language
        
        Respond with a JSON object containing:
        {
            "sentiment": "happy" | "neutral" | "mad",
            "confidence": 0.0-1.0,
            "reasoning": "brief explanation"
        }"""
        
        try:
            response = await self.openai_service.get_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this conversation:\n\n{conversation_text}"}
                ],
                model="gpt-4o-mini",
                temperature=0.3,
                max_tokens=200
            )
            
            # Parse response
            result = json.loads(response)
            sentiment = result.get("sentiment", "neutral")
            confidence = float(result.get("confidence", 0.5))
            
            # Validate sentiment
            if sentiment not in ["happy", "neutral", "mad"]:
                sentiment = "neutral"
                
            logger.info(f"Sentiment analysis result: {sentiment} (confidence: {confidence})")
            return sentiment, confidence
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return "neutral", 0.0
    
    async def update_call_sentiment(self, db: AsyncSession, call_id: str) -> Optional[dict]:
        """
        Analyze and update sentiment for a call
        Returns sentiment update data or None
        """
        try:
            # Get the call
            result = await db.execute(
                select(Call).where(Call.id == call_id)
            )
            call = result.scalar_one_or_none()
            if not call or call.status != "active":
                return None
                
            # Get recent transcriptions (last 60 seconds)
            cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=60)
            result = await db.execute(
                select(Transcription)
                .where(
                    Transcription.call_id == call_id,
                    Transcription.timestamp >= cutoff_time
                )
                .order_by(Transcription.timestamp)
            )
            recent_transcriptions = result.scalars().all()
            
            if not recent_transcriptions:
                return None
                
            # Analyze sentiment
            sentiment, confidence = await self.analyze_sentiment(recent_transcriptions)
            
            # Update call record
            call.current_sentiment = sentiment
            call.sentiment_confidence = confidence
            call.sentiment_updated_at = datetime.now(timezone.utc)
            
            # Create history record
            context_preview = " | ".join([f"{t.speaker}: {t.text[:50]}..." for t in recent_transcriptions[-3:]])
            history = SentimentHistory(
                call_id=call_id,
                sentiment=sentiment,
                confidence=confidence,
                transcription_context=context_preview
            )
            db.add(history)
            
            await db.commit()
            
            return {
                "call_id": str(call_id),
                "sentiment": sentiment,
                "confidence": confidence,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating call sentiment: {e}")
            await db.rollback()
            return None
    
    async def get_sentiment_history(self, db: AsyncSession, call_id: str) -> List[dict]:
        """Get sentiment history for a call"""
        result = await db.execute(
            select(SentimentHistory)
            .where(SentimentHistory.call_id == call_id)
            .order_by(desc(SentimentHistory.timestamp))
        )
        history = result.scalars().all()
        
        return [
            {
                "sentiment": h.sentiment,
                "confidence": h.confidence,
                "timestamp": h.timestamp.isoformat(),
                "context": h.transcription_context
            }
            for h in history
        ]


# Singleton instance
sentiment_service = SentimentAnalysisService()