from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import logging
from models import Call, Transcription, AIInteraction, CallSummary, CallDocumentReference
from .bedrock_service import BedrockService
from .vector_search import VectorSearchService
from websocket.manager import websocket_manager

logger = logging.getLogger(__name__)


class CallProcessor:
    def __init__(self):
        self.bedrock_service = BedrockService()
        self.vector_service = VectorSearchService()
        self.context_window_minutes = 2
        self.min_transcriptions_for_search = 2  # Start searching after just 2 transcriptions
        
    async def process_transcription(
        self,
        transcription_id: str,
        call_id: str,
        db: AsyncSession
    ):
        """Process new transcription and search for relevant documents"""
        
        logger.info(f"🔍 STARTING VECTOR SEARCH FLOW for call {call_id}, transcription {transcription_id}")
        
        try:
            # Get recent transcriptions for context
            recent_transcriptions = await self._get_recent_transcriptions(
                db, call_id, self.context_window_minutes
            )
            
            logger.info(f"📝 Found {len(recent_transcriptions)} recent transcriptions for call {call_id}")
            if recent_transcriptions:
                logger.info(f"   Latest: {recent_transcriptions[-1].get('text', '')[:100]}...")
            
            # Only process if we have enough context
            if len(recent_transcriptions) < self.min_transcriptions_for_search:
                logger.info(f"Not enough transcriptions for call {call_id} yet (have {len(recent_transcriptions)}, need {self.min_transcriptions_for_search})")
                return
                
            # Analyze conversation context
            logger.info(f"🤖 Analyzing conversation with Bedrock Nova...")
            summary, topics = await self.bedrock_service.analyze_conversation_context(
                recent_transcriptions
            )
            
            logger.info(f"📊 Bedrock Analysis Results:")
            logger.info(f"   Summary: {summary}")
            logger.info(f"   Topics: {topics}")
            
            if not summary and not topics:
                logger.warning(f"⚠️ No meaningful context extracted for call {call_id}")
                return
                
            # Generate search query
            search_query = await self.bedrock_service.generate_search_query(
                summary, topics
            )
            logger.info(f"🔎 Generated search query: '{search_query}'")
            
            # Search for relevant documents
            logger.info(f"🔍 Searching vector store...")
            documents = await self.vector_service.search_documents(
                search_query,
                db,
                limit=5,
                similarity_threshold=0.3  # Lower threshold to be more inclusive
            )
            
            logger.info(f"📚 Found {len(documents)} relevant documents for call {call_id}")
            if documents:
                for i, doc in enumerate(documents[:3], 1):
                    logger.info(f"   {i}. {doc['title']} (similarity: {doc['similarity']:.2f})")
            
            if documents:
                # Store AI interaction
                ai_interaction = AIInteraction(
                    call_id=call_id,
                    transcription_id=transcription_id,
                    prompt=search_query,
                    response=summary,
                    vector_search_results=documents,
                    relevance_score=documents[0]["similarity"] if documents else 0
                )
                db.add(ai_interaction)
                
                # Store document references
                for doc in documents[:3]:  # Top 3 documents
                    doc_ref = CallDocumentReference(
                        call_id=call_id,
                        document_id=doc["document_id"],
                        document_title=doc["title"],
                        relevance_score=doc["similarity"],
                        context=summary
                    )
                    db.add(doc_ref)
                
                await db.commit()
                
                # Send suggestions via WebSocket
                logger.info(f"📡 Broadcasting AI suggestions for call {call_id} with {len(documents)} documents")
                broadcast_result = await websocket_manager.broadcast_to_call(
                    call_id,
                    {
                        "event": "ai:suggestion",
                        "data": {
                            "call_id": call_id,
                            "documents": documents,
                            "summary": summary,
                            "topics": topics
                        }
                    }
                )
                logger.info(f"✅ Broadcast complete. Result: {broadcast_result}")
                
            logger.info(f"✅ VECTOR SEARCH COMPLETE for call {call_id}, found {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"❌ ERROR in vector search flow: {e}", exc_info=True)
            await db.rollback()
            
    async def generate_call_summary(
        self,
        call_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Generate summary for completed call"""
        
        try:
            # Get all transcriptions for the call
            result = await db.execute(
                select(Transcription)
                .where(Transcription.call_id == call_id)
                .order_by(Transcription.timestamp)
            )
            transcriptions = result.scalars().all()
            
            if not transcriptions:
                return {"error": "No transcriptions found"}
                
            # Format transcriptions
            trans_data = [
                {
                    "speaker": t.speaker,
                    "text": t.text,
                    "timestamp": t.timestamp.isoformat()
                }
                for t in transcriptions
            ]
            
            # Generate summary using Bedrock
            summary_data = await self.bedrock_service.summarize_call(trans_data)
            
            # Store summary in database
            call_summary = CallSummary(
                call_id=call_id,
                summary=summary_data["summary"],
                key_topics=summary_data["key_topics"],
                sentiment_score=summary_data["sentiment_score"],
                action_items=summary_data["action_items"],
                meta_data={
                    "sentiment": summary_data["sentiment"],
                    "transcription_count": len(transcriptions)
                }
            )
            
            db.add(call_summary)
            await db.commit()
            
            # Send summary via WebSocket
            await websocket_manager.broadcast_to_call(
                call_id,
                {
                    "event": "call:summary",
                    "data": {
                        "call_id": call_id,
                        "summary": summary_data
                    }
                }
            )
            
            return summary_data
            
        except Exception as e:
            logger.error(f"Error generating call summary: {e}")
            await db.rollback()
            return {"error": str(e)}
            
    async def _get_recent_transcriptions(
        self,
        db: AsyncSession,
        call_id: str,
        minutes: int
    ) -> List[Dict[str, Any]]:
        """Get recent transcriptions for a call"""
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        result = await db.execute(
            select(Transcription)
            .where(and_(
                Transcription.call_id == call_id,
                Transcription.timestamp >= cutoff_time
            ))
            .order_by(Transcription.timestamp.desc())
            .limit(10)
        )
        
        transcriptions = result.scalars().all()
        
        return [
            {
                "speaker": t.speaker,
                "text": t.text,
                "timestamp": t.timestamp.isoformat()
            }
            for t in reversed(transcriptions)  # Chronological order
        ]