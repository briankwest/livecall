"""Test endpoint for vector search flow"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime, timezone

from core.database import get_db
from services.call_processor import CallProcessor
from services.bedrock_service import BedrockService
from services.vector_search import VectorSearchService
from models import Call, Transcription
import logging

router = APIRouter(prefix="/api/test", tags=["test"])
logger = logging.getLogger(__name__)


class TestTranscription(BaseModel):
    speaker: str
    text: str


class TestVectorSearchRequest(BaseModel):
    transcriptions: List[TestTranscription]
    call_id: Optional[str] = None


@router.post("/vector-search")
async def test_vector_search(
    request: TestVectorSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Test the vector search flow with simulated transcriptions"""
    
    logger.info("🧪 TEST: Starting vector search test")
    
    try:
        # Create a test call if not provided
        call_id = request.call_id or str(uuid.uuid4())
        
        # Check if call exists (convert string to UUID)
        from uuid import UUID
        call_uuid = UUID(call_id) if isinstance(call_id, str) else call_id
        existing_call = await db.get(Call, call_uuid)
        if not existing_call:
            # Create test call
            test_call = Call(
                id=call_uuid,
                signalwire_call_id=f"test_{call_id}",
                phone_number="+1234567890",
                agent_id="test_agent",
                start_time=datetime.now(timezone.utc),
                status="active",
                listening_mode="both",
                direction="outbound"
            )
            db.add(test_call)
            await db.commit()
            logger.info(f"Created test call: {call_uuid}")
        
        # Create test transcriptions
        transcription_ids = []
        for i, trans in enumerate(request.transcriptions):
            trans_uuid = uuid.uuid4()
            transcription = Transcription(
                id=trans_uuid,
                call_id=call_uuid,
                speaker=trans.speaker,
                text=trans.text,
                confidence=0.95,
                timestamp=datetime.now(timezone.utc),
                sequence_number=i
            )
            db.add(transcription)
            transcription_ids.append(trans_uuid)
        
        await db.commit()
        logger.info(f"Created {len(transcription_ids)} test transcriptions")
        
        # Process the last transcription (triggers vector search)
        call_processor = CallProcessor()
        await call_processor.process_transcription(
            transcription_ids[-1],
            call_uuid,
            db
        )
        
        # Also test direct Bedrock analysis
        bedrock = BedrockService()
        trans_data = [{"speaker": t.speaker, "text": t.text} for t in request.transcriptions]
        summary, topics = await bedrock.analyze_conversation_context(trans_data)
        
        # Test vector search directly
        vector_service = VectorSearchService()
        search_query = await bedrock.generate_search_query(summary, topics)
        documents = await vector_service.search_documents(
            search_query,
            db,
            limit=5,
            similarity_threshold=0.3
        )
        
        return {
            "status": "success",
            "call_id": call_id,
            "transcription_count": len(transcription_ids),
            "analysis": {
                "summary": summary,
                "topics": topics,
                "search_query": search_query
            },
            "documents_found": len(documents),
            "documents": documents[:3] if documents else []
        }
        
    except Exception as e:
        logger.error(f"Test vector search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-refund-search")
async def test_refund_search(
    db: AsyncSession = Depends(get_db)
):
    """Quick test with refund-related conversation"""
    
    test_data = TestVectorSearchRequest(
        transcriptions=[
            TestTranscription(speaker="customer", text="Hi, I need help with something"),
            TestTranscription(speaker="agent", text="Hello! I'd be happy to help. What can I assist you with today?"),
            TestTranscription(speaker="customer", text="I bought a product last week and it arrived damaged. I want to get my money back"),
            TestTranscription(speaker="agent", text="I'm sorry to hear that. Let me help you with the refund process"),
            TestTranscription(speaker="customer", text="How long does the refund take?")
        ]
    )
    
    return await test_vector_search(test_data, db)