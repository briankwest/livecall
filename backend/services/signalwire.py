from typing import Dict, Any, Optional
from datetime import datetime
import logging
import hashlib
import hmac
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Call, Transcription, CallStatus, ListeningMode
from core.config import settings

logger = logging.getLogger(__name__)


class SignalWireService:
    def __init__(self):
        self.project_id = settings.signalwire_project_id
        self.token = settings.signalwire_token
        
    def verify_webhook_signature(self, signature: str, body: bytes) -> bool:
        """Verify SignalWire webhook signature"""
        if not self.token:
            logger.warning("SignalWire token not configured, skipping signature verification")
            return True
            
        expected_signature = hmac.new(
            self.token.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    async def handle_transcription_event(
        self,
        event_data: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Handle live transcription events from SignalWire"""
        
        call_id = event_data.get("call_id")
        text = event_data.get("text", "").strip()
        speaker = event_data.get("speaker")  # 'inbound' or 'outbound'
        confidence = event_data.get("confidence", 1.0)
        is_final = event_data.get("is_final", True)
        
        if not call_id or not text:
            return {"status": "ignored", "reason": "missing required fields"}
        
        # Get or create call
        call = await self._get_or_create_call(db, call_id, event_data)
        
        # Check listening mode
        if not self._should_process_speaker(call.listening_mode, speaker):
            return {"status": "ignored", "reason": "speaker not in listening mode"}
        
        # Only process final transcriptions
        if not is_final:
            return {"status": "ignored", "reason": "interim result"}
        
        # Create transcription record
        transcription = Transcription(
            call_id=call.id,
            speaker=self._normalize_speaker(speaker),
            text=text,
            confidence=confidence,
            timestamp=datetime.utcnow()
        )
        
        db.add(transcription)
        await db.commit()
        await db.refresh(transcription)
        
        return {
            "status": "success",
            "transcription_id": str(transcription.id),
            "call_id": str(call.id)
        }
    
    async def handle_call_status_event(
        self,
        event_data: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Handle call status events from SignalWire"""
        
        call_id = event_data.get("call_id")
        status = event_data.get("status")
        
        if not call_id:
            return {"status": "error", "reason": "missing call_id"}
        
        # Find existing call
        result = await db.execute(
            select(Call).where(Call.signalwire_call_id == call_id)
        )
        call = result.scalar_one_or_none()
        
        if not call:
            # Create new call if it doesn't exist
            call = await self._get_or_create_call(db, call_id, event_data)
        
        # Update call with timing information if provided
        if event_data.get("start_time") and not call.start_time:
            # Convert milliseconds to datetime
            call.start_time = datetime.fromtimestamp(event_data["start_time"] / 1000)
        
        # Update call status
        if status == "completed":
            call.status = CallStatus.ENDED
            if event_data.get("end_time"):
                call.end_time = datetime.fromtimestamp(event_data["end_time"] / 1000)
            else:
                call.end_time = datetime.utcnow()
            
            # Calculate duration from actual times if available
            if event_data.get("answer_time") and event_data.get("end_time"):
                duration = (event_data["end_time"] - event_data["answer_time"]) / 1000
                call.duration_seconds = int(duration)
            elif call.start_time and call.end_time:
                duration = (call.end_time - call.start_time).total_seconds()
                call.duration_seconds = int(duration)
        elif status == "failed":
            call.status = CallStatus.FAILED
            if event_data.get("end_time"):
                call.end_time = datetime.fromtimestamp(event_data["end_time"] / 1000)
            else:
                call.end_time = datetime.utcnow()
        
        await db.commit()
        
        return {
            "status": "success",
            "call_id": str(call.id),
            "call_status": call.status.value
        }
    
    async def _get_or_create_call(
        self,
        db: AsyncSession,
        signalwire_call_id: str,
        event_data: Dict[str, Any]
    ) -> Call:
        """Get existing call or create new one"""
        
        result = await db.execute(
            select(Call).where(Call.signalwire_call_id == signalwire_call_id)
        )
        call = result.scalar_one_or_none()
        
        if not call:
            # Use to (destination) as the primary phone number for customer calls
            phone_number = event_data.get("to") or event_data.get("from") or event_data.get("destination_number")
            
            call = Call(
                signalwire_call_id=signalwire_call_id,
                phone_number=phone_number,
                agent_id=event_data.get("agent_id"),
                status=CallStatus.ACTIVE,
                listening_mode=ListeningMode(event_data.get("listening_mode", "both"))
            )
            
            # Set start time if provided
            if event_data.get("start_time"):
                call.start_time = datetime.fromtimestamp(event_data["start_time"] / 1000)
            
            db.add(call)
            await db.commit()
            await db.refresh(call)
            
        return call
    
    def _normalize_speaker(self, speaker: str) -> str:
        """Normalize speaker value from SignalWire to our format"""
        speaker_map = {
            "inbound": "customer",
            "outbound": "agent",
            "remote-caller": "customer",
            "local-caller": "agent",
            "remote_caller": "customer",  # Alternative format
            "local_caller": "agent"       # Alternative format
        }
        return speaker_map.get(speaker.lower(), speaker)
    
    def _should_process_speaker(self, listening_mode: ListeningMode, speaker: str) -> bool:
        """Check if we should process this speaker based on listening mode"""
        normalized_speaker = self._normalize_speaker(speaker)
        
        if listening_mode == ListeningMode.BOTH:
            return True
        elif listening_mode == ListeningMode.AGENT:
            return normalized_speaker == "agent"
        elif listening_mode == ListeningMode.CUSTOMER:
            return normalized_speaker == "customer"
        
        return False