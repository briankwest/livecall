from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime
import logging
from core.database import get_db
from core.security import get_current_user
from models import Call, Transcription, CallSummary, CallDocumentReference, User
from services.call_processor import CallProcessor
from services.signalwire_service import SignalWireService
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/calls", tags=["calls"])
logger = logging.getLogger(__name__)


class CallResponse(BaseModel):
    id: str
    signalwire_call_id: str
    phone_number: Optional[str]
    agent_id: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[int]
    status: str
    listening_mode: str
    transcription_count: Optional[int] = 0
    documents_accessed: Optional[int] = 0


class TranscriptionResponse(BaseModel):
    id: str
    speaker: str
    text: str
    confidence: Optional[float]
    timestamp: datetime


class CallSummaryResponse(BaseModel):
    summary: str
    key_topics: List[str]
    sentiment_score: float
    action_items: List[str]
    meta_data: dict


@router.get("/", response_model=List[CallResponse])
async def list_calls(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List calls with pagination"""
    
    query = select(Call)
    
    if status:
        query = query.where(Call.status == status)
        
    query = query.order_by(desc(Call.start_time)).offset(skip).limit(limit)
    
    result = await db.execute(query)
    calls = result.scalars().all()
    
    response = []
    for call in calls:
        # Get counts
        trans_result = await db.execute(
            select(Transcription).where(Transcription.call_id == call.id)
        )
        trans_count = len(trans_result.scalars().all())
        
        doc_result = await db.execute(
            select(CallDocumentReference).where(CallDocumentReference.call_id == call.id)
        )
        doc_count = len(doc_result.scalars().all())
        
        response.append(CallResponse(
            id=str(call.id),
            signalwire_call_id=call.signalwire_call_id,
            phone_number=call.phone_number,
            agent_id=call.agent_id,
            start_time=call.start_time,
            end_time=call.end_time,
            duration_seconds=call.duration_seconds,
            status=call.status,
            listening_mode=call.listening_mode,
            transcription_count=trans_count,
            documents_accessed=doc_count
        ))
        
    return response


@router.get("/{call_id}", response_model=CallResponse)
async def get_call(
    call_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get call details"""
    
    result = await db.execute(
        select(Call).where(Call.id == call_id)
    )
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
        
    # Get counts
    trans_result = await db.execute(
        select(Transcription).where(Transcription.call_id == call.id)
    )
    trans_count = len(trans_result.scalars().all())
    
    doc_result = await db.execute(
        select(CallDocumentReference).where(CallDocumentReference.call_id == call.id)
    )
    doc_count = len(doc_result.scalars().all())
    
    return CallResponse(
        id=str(call.id),
        signalwire_call_id=call.signalwire_call_id,
        phone_number=call.phone_number,
        agent_id=call.agent_id,
        start_time=call.start_time,
        end_time=call.end_time,
        duration_seconds=call.duration_seconds,
        status=call.status.value,
        listening_mode=call.listening_mode.value,
        transcription_count=trans_count,
        documents_accessed=doc_count
    )


@router.get("/{call_id}/transcripts", response_model=List[TranscriptionResponse])
async def get_call_transcripts(
    call_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all transcriptions for a call"""
    
    result = await db.execute(
        select(Transcription)
        .where(Transcription.call_id == call_id)
        .order_by(Transcription.timestamp)
    )
    transcriptions = result.scalars().all()
    
    return [
        TranscriptionResponse(
            id=str(t.id),
            speaker=t.speaker,
            text=t.text,
            confidence=t.confidence,
            timestamp=t.timestamp
        )
        for t in transcriptions
    ]


@router.get("/{call_id}/summary", response_model=CallSummaryResponse)
async def get_call_summary(
    call_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get call summary"""
    
    result = await db.execute(
        select(CallSummary).where(CallSummary.call_id == call_id)
    )
    summary = result.scalar_one_or_none()
    
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
        
    return CallSummaryResponse(
        summary=summary.summary,
        key_topics=summary.key_topics or [],
        sentiment_score=summary.sentiment_score or 0.5,
        action_items=summary.action_items or [],
        meta_data=summary.meta_data or {}
    )


@router.post("/{call_id}/end")
async def end_call(
    call_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually end a call"""
    
    result = await db.execute(
        select(Call).where(Call.id == call_id)
    )
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
        
    if call.status != "active":
        raise HTTPException(status_code=400, detail="Call is not active")
        
    # Update call status
    call.status = "ended"
    call.end_time = datetime.utcnow()
    if call.start_time:
        duration = (call.end_time - call.start_time).total_seconds()
        call.duration_seconds = int(duration)
        
    await db.commit()
    
    # Generate summary
    processor = CallProcessor()
    summary = await processor.generate_call_summary(call_id, db)
    
    return {"status": "success", "summary": summary}


class InitiateCallRequest(BaseModel):
    to_number: str = Field(..., description="Phone number to call (E.164 format)")
    agent_name: str = Field(..., description="Name of the agent making the call")
    listening_mode: str = Field(default="both", description="Listening mode: agent, customer, or both")
    call_reason: Optional[str] = Field(None, description="Reason for the call")
    webrtc_call_id: Optional[str] = Field(None, description="WebRTC call ID if tracking an existing WebPhone call")
    from_number: Optional[str] = Field(None, description="From number for inbound calls")
    direction: Optional[str] = Field(None, description="Call direction: inbound or outbound")


class InitiateCallResponse(BaseModel):
    call_id: str
    signalwire_call_id: str
    status: str
    message: str


@router.post("/initiate", response_model=InitiateCallResponse)
async def initiate_call(
    request: InitiateCallRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Initiate a new call with SignalWire or track a WebRTC call"""
    
    try:
        # Check if this is a WebRTC call (has webrtc_call_id)
        webrtc_call_id = getattr(request, 'webrtc_call_id', None)
        
        if webrtc_call_id:
            # This is a WebRTC call from WebPhone - just track it
            logger.info(f"Tracking WebRTC call: {webrtc_call_id}")
            
            # Create call record in database
            new_call = Call(
                signalwire_call_id=webrtc_call_id,  # Use WebRTC ID as the SignalWire ID
                phone_number=request.to_number,
                agent_id=current_user.username,
                status="active",  # WebRTC calls are active when we get them
                listening_mode=request.listening_mode
            )
            
            db.add(new_call)
            await db.commit()
            await db.refresh(new_call)
            
            # Notify via WebSocket
            from websocket.manager import websocket_manager
            await websocket_manager.broadcast_to_user(
                current_user.username,
                {
                    "event": "call:initiated",
                    "data": {
                        "call_id": str(new_call.id),
                        "signalwire_call_id": new_call.signalwire_call_id,
                        "to_number": request.to_number,
                        "status": "active",
                        "is_webrtc": True
                    }
                }
            )
            
            return InitiateCallResponse(
                call_id=str(new_call.id),
                signalwire_call_id=new_call.signalwire_call_id,
                status="active",
                message="WebRTC call tracked successfully"
            )
        else:
            # This is a regular SignalWire API call
            # Initialize SignalWire service
            signalwire = SignalWireService()
            
            # Place the call
            call_result = await signalwire.place_call(
                to_number=request.to_number,
                agent_name=request.agent_name,
                listening_mode=request.listening_mode
            )
            
            # Create call record in database
            new_call = Call(
                signalwire_call_id=call_result["signalwire_call_id"],
                phone_number=request.to_number,
                agent_id=current_user.username,
                status="initiated",
                listening_mode=request.listening_mode
            )
            
            db.add(new_call)
            await db.commit()
            await db.refresh(new_call)
            
            # Log the call initiation
            logger.info(f"Call initiated: {new_call.id} to {request.to_number}")
            
            # Notify via WebSocket
            from websocket.manager import websocket_manager
            await websocket_manager.broadcast_to_user(
                current_user.username,
                {
                    "event": "call:initiated",
                    "data": {
                        "call_id": str(new_call.id),
                        "signalwire_call_id": new_call.signalwire_call_id,
                        "to_number": request.to_number,
                        "status": "initiated"
                    }
                }
            )
            
            return InitiateCallResponse(
                call_id=str(new_call.id),
                signalwire_call_id=new_call.signalwire_call_id,
                status="initiated",
                message="Call is being placed"
            )
        
    except Exception as e:
        logger.error(f"Failed to initiate call: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate call: {str(e)}"
        )