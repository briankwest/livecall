from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import logging
import json
from datetime import datetime
from core.database import get_db
from services.signalwire import SignalWireService
from services.call_processor import CallProcessor
from websocket.manager import websocket_manager

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


@router.post("/signalwire/transcribe")
async def signalwire_transcribe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Handle SignalWire live transcription webhook"""
    
    # Get raw body for signature verification
    body = await request.body()
    
    # Verify webhook signature
    signalwire_service = SignalWireService()
    signature = request.headers.get("X-SignalWire-Signature", "")
    
    if not signalwire_service.verify_webhook_signature(signature, body):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    # Parse JSON data
    data = await request.json()
    logger.info(f"Received transcription webhook: {data}")
    
    # Handle transcription event
    result = await signalwire_service.handle_transcription_event(data, db)
    
    # If transcription was created, process it in the background
    if result["status"] == "success":
        call_processor = CallProcessor()
        background_tasks.add_task(
            call_processor.process_transcription,
            result["transcription_id"],
            result["call_id"],
            db
        )
        
        # Broadcast transcription to WebSocket clients
        await websocket_manager.broadcast_to_call(
            result["call_id"],
            {
                "event": "transcription:update",
                "data": {
                    "call_id": result["call_id"],
                    "transcription_id": result["transcription_id"],
                    "speaker": data.get("speaker"),
                    "text": data.get("text"),
                    "timestamp": data.get("timestamp")
                }
            }
        )
    
    return result


@router.post("/signalwire/status")
async def signalwire_status_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Handle SignalWire call status webhook"""
    
    # Get raw body for signature verification
    body = await request.body()
    
    # Verify webhook signature
    signalwire_service = SignalWireService()
    signature = request.headers.get("X-SignalWire-Signature", "")
    
    if not signalwire_service.verify_webhook_signature(signature, body):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    # Parse JSON data
    data = await request.json()
    logger.info(f"Received status webhook: {data}")
    
    # Handle status event
    result = await signalwire_service.handle_call_status_event(data, db)
    
    # Broadcast status update to WebSocket clients
    if result["status"] == "success":
        await websocket_manager.broadcast_to_call(
            result["call_id"],
            {
                "event": "call:status",
                "data": {
                    "call_id": result["call_id"],
                    "status": result["call_status"]
                }
            }
        )
    
    return result


@router.post("/swml")
@router.get("/swml")
async def swml_webhook(request: Request) -> Dict[str, Any]:
    """Return SWML configuration for calls with live transcription - NO AUTH REQUIRED"""
    
    from core.config import settings
    
    # Log the full request details for debugging
    logger.info(f"SWML webhook called - Method: {request.method}")
    logger.info(f"Headers: {dict(request.headers)}")
    
    # Get variables from the request - SignalWire sends them differently based on the request
    destination_number = ""
    from_number = settings.signalwire_from_number or "+12544645483"  # Use the from_number from env
    
    # Try to get parameters from different sources
    if request.method == "POST":
        try:
            # SignalWire might send form data
            form_data = await request.form()
            logger.info(f"Form data: {dict(form_data)}")
            
            # Check for userVariables in form data
            user_vars_str = form_data.get("userVariables", "")
            if user_vars_str:
                import json
                try:
                    user_vars = json.loads(user_vars_str)
                    destination_number = user_vars.get("destination_number", "")
                except:
                    pass
            
            # Also check direct form fields
            if not destination_number:
                destination_number = form_data.get("destination_number", "")
                
        except:
            # Try JSON body
            try:
                body = await request.json()
                logger.info(f"JSON body: {body}")
                user_vars = body.get("userVariables", body)
                destination_number = user_vars.get("destination_number", "")
            except:
                pass
    else:
        # GET request - check query parameters
        destination_number = request.query_params.get("destination_number", "")
        logger.info(f"Query params: {dict(request.query_params)}")
    
    # Use the base URL from settings
    base_url = settings.public_url
    
    if not destination_number:
        logger.error("No destination number provided in request")
        # For testing, use a default number
        destination_number = "+19184238080"  # Default test number
    
    logger.info(f"Generating SWML for call to {destination_number} from {from_number}")
    logger.info(f"Base URL: {base_url}")
    
    # Build the complete SWML response using userVariables
    swml_response = {
        "version": "1.0.0",
        "sections": {
            "main": [
                {
                    "record_call": {
                        "format": "mp3",
                        "stereo": True,
                        "direction": "both",
                        "beep": False,
                        "status_url": f"{base_url}/api/webhooks/recording-status"
                    }
                },
                {
                    "live_transcribe": {
                        "action": {
                            "start": {
                                "webhook": f"{base_url}/api/webhooks/transcription",
                                "lang": "en",
                                "live_events": True,
                                "ai_summary": True,
                                "debug_level": 2,
                                "direction": [
                                    "remote-caller",
                                    "local-caller"
                                ]
                            }
                        }
                    }
                },
                {
                    "connect": {
                        "to": "%{vars.userVariables.destination_number}",
                        "from": "%{vars.userVariables.from_number}",
                        "timeout": 30,
                        "answer_on_bridge": False,
                        "call_state_events": ["created", "ringing", "answered", "ended"],
                        "call_state_url": f"{base_url}/api/webhooks/call-state"
                    }
                }
            ]
        }
    }
    
    logger.info(f"Returning SWML: {swml_response}")
    return swml_response


@router.post("/transcription")
async def handle_transcription(
    request: Request, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Handle live transcription webhooks from SignalWire"""
    
    try:
        data = await request.json()
        logger.info("="*80)
        logger.info("TRANSCRIPTION WEBHOOK RECEIVED")
        logger.info("="*80)
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Full payload: {json.dumps(data, indent=2)}")
        
        # Extract transcription details from SignalWire format
        utterance = data.get("utterance", {})
        text = utterance.get("content", "")
        speaker = utterance.get("role", "unknown")
        # Confidence is at top level, not in utterance
        confidence = data.get("confidence", 1.0)
        
        # Get call info
        call_info = data.get("call_info", {})
        call_id = call_info.get("call_id", "")
        
        # Get timestamp from utterance
        timestamp = utterance.get("timestamp", 0)
        
        # Get channel data for user variables (destination number, etc)
        channel_data = data.get("channel_data", {})
        swml_vars = channel_data.get("SWMLVars", {})
        user_vars = swml_vars.get("userVariables", {})
        
        # Log specific fields for database mapping
        logger.info("Extracted fields for database:")
        logger.info(f"  - text: {text}")
        logger.info(f"  - speaker: {speaker}")
        logger.info(f"  - confidence: {confidence}")
        logger.info(f"  - call_id: {call_id}")
        logger.info(f"  - timestamp: {timestamp}")
        logger.info(f"  - lang: {utterance.get('lang', 'NOT PROVIDED')}")
        logger.info(f"  - tokens: {utterance.get('tokens', 'NOT PROVIDED')}")
        logger.info(f"  - user_vars: {user_vars}")
        logger.info("="*80)
        
        # Skip empty transcriptions
        if not text.strip():
            return {"status": "ignored", "reason": "empty transcription"}
        
        # Map speaker role to our format
        speaker_mapped = "customer" if speaker == "remote-caller" else "agent" if speaker == "local-caller" else speaker
        
        # Get or create call record
        from sqlalchemy import select
        from models import Call, Transcription
        
        result = await db.execute(
            select(Call).where(Call.signalwire_call_id == call_id)
        )
        call = result.scalar_one_or_none()
        
        if not call:
            # Create new call record
            call = Call(
                signalwire_call_id=call_id,
                phone_number=user_vars.get("destination_number", "Unknown"),
                status="active",
                listening_mode="both",
                raw_data=data  # Store the entire webhook payload
            )
            db.add(call)
            await db.commit()
            await db.refresh(call)
            logger.info(f"Created new call record: {call.id}")
        
        # Create transcription record
        transcription = Transcription(
            call_id=call.id,
            speaker=speaker_mapped,
            text=text,
            confidence=confidence,
            timestamp=datetime.fromtimestamp(timestamp / 1000000) if timestamp else datetime.utcnow(),  # Convert microseconds
            raw_data=data  # Store the entire webhook payload
        )
        db.add(transcription)
        await db.commit()
        await db.refresh(transcription)
        
        result = {"status": "success", "transcription_id": str(transcription.id), "call_id": str(call.id)}
        
        # If transcription was created, process it and broadcast via WebSocket
        if result["status"] == "success":
            # Process in background
            call_processor = CallProcessor()
            background_tasks.add_task(
                call_processor.process_transcription,
                result["transcription_id"],
                result["call_id"],
                db
            )
            
            # Broadcast to WebSocket clients
            await websocket_manager.broadcast_to_call(
                result["call_id"],
                {
                    "event": "transcription:update",
                    "data": {
                        "call_id": result["call_id"],
                        "transcription_id": result["transcription_id"],
                        "speaker": speaker_mapped,
                        "text": text,
                        "timestamp": str(transcription.timestamp),
                        "confidence": confidence
                    }
                }
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing transcription: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}


@router.post("/call-state")
async def handle_call_state(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle call state updates from SignalWire"""
    
    try:
        data = await request.json()
        logger.info("="*80)
        logger.info("CALL STATE WEBHOOK RECEIVED")
        logger.info("="*80)
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Full payload: {json.dumps(data, indent=2)}")
        
        # Extract fields from SignalWire format
        logger.info("="*80)
        logger.info("PARSING CALL STATE DATA")
        logger.info("="*80)
        
        # Top level fields
        event_type = data.get("event_type", "")
        event_channel = data.get("event_channel", "")
        timestamp = data.get("timestamp", 0)
        project_id = data.get("project_id", "")
        space_id = data.get("space_id", "")
        
        logger.info("TOP LEVEL FIELDS:")
        logger.info(f"  event_type: {event_type}")
        logger.info(f"  event_channel: {event_channel}")
        logger.info(f"  timestamp: {timestamp}")
        logger.info(f"  project_id: {project_id}")
        logger.info(f"  space_id: {space_id}")
        
        # Params fields
        params = data.get("params", {})
        call_id = params.get("call_id", "")
        node_id = params.get("node_id", "")
        segment_id = params.get("segment_id", "")
        call_state = params.get("call_state", "")
        direction = params.get("direction", "")
        
        logger.info("\nPARAMS FIELDS:")
        logger.info(f"  call_id: {call_id}")
        logger.info(f"  node_id: {node_id}")
        logger.info(f"  segment_id: {segment_id}")
        logger.info(f"  call_state: {call_state}")
        logger.info(f"  direction: {direction}")
        
        # Parent info (if exists)
        parent = params.get("parent", {})
        if parent:
            logger.info("\nPARENT CALL INFO:")
            logger.info(f"  device_type: {parent.get('device_type', '')}")
            logger.info(f"  call_id: {parent.get('call_id', '')}")
            logger.info(f"  node_id: {parent.get('node_id', '')}")
        
        # Peer info (if exists)
        peer = params.get("peer", {})
        if peer:
            logger.info("\nPEER INFO:")
            logger.info(f"  call_id: {peer.get('call_id', '')}")
            logger.info(f"  node_id: {peer.get('node_id', '')}")
        
        # Device info (if exists)
        device = params.get("device", {})
        if device:
            logger.info("\nDEVICE INFO:")
            logger.info(f"  type: {device.get('type', '')}")
            device_params = device.get("params", {})
            if device_params:
                logger.info(f"  from_number: {device_params.get('from_number', '')}")
                logger.info(f"  to_number: {device_params.get('to_number', '')}")
                logger.info(f"  headers: {device_params.get('headers', [])}")
        
        # Timing info (if exists)
        start_time = params.get("start_time", 0)
        answer_time = params.get("answer_time", 0)
        end_time = params.get("end_time", 0)
        
        if start_time or answer_time or end_time:
            logger.info("\nTIMING INFO:")
            logger.info(f"  start_time: {start_time}")
            logger.info(f"  answer_time: {answer_time}")
            logger.info(f"  end_time: {end_time}")
            
            # Calculate duration if ended
            if call_state == "ended" and answer_time and end_time:
                duration = (end_time - answer_time) / 1000  # Convert to seconds
                logger.info(f"  duration: {duration} seconds")
        
        # End reason and quality (if exists)
        end_reason = params.get("end_reason", "")
        end_source = params.get("end_source", "")
        audio_in_mos = params.get("audio_in_mos", "")
        
        if end_reason or end_source or audio_in_mos:
            logger.info("\nCALL END INFO:")
            logger.info(f"  end_reason: {end_reason}")
            logger.info(f"  end_source: {end_source}")
            logger.info(f"  audio_in_mos: {audio_in_mos}")
        
        # Any other fields not captured above
        known_fields = {"call_id", "node_id", "segment_id", "call_state", "direction", 
                       "parent", "peer", "device", "start_time", "answer_time", "end_time",
                       "end_reason", "end_source", "audio_in_mos"}
        other_fields = {k: v for k, v in params.items() if k not in known_fields}
        
        if other_fields:
            logger.info("\nOTHER FIELDS:")
            for key, value in other_fields.items():
                logger.info(f"  {key}: {value}")
        logger.info("="*80)
        
        # Handle call state update
        from sqlalchemy import select
        from models import Call
        
        # Use parent call ID if this is a child call (PSTN leg)
        # The parent call is the WebRTC call from the browser
        search_call_id = parent.get("call_id") if parent else call_id
        
        result = await db.execute(
            select(Call).where(Call.signalwire_call_id == search_call_id)
        )
        call = result.scalar_one_or_none()
        
        if not call and call_state == "created":
            # Create new call record
            phone_number = device.get("params", {}).get("to_number") if device else "Unknown"
            call = Call(
                signalwire_call_id=search_call_id,
                phone_number=phone_number,
                status="active",
                listening_mode="both",
                raw_data=data  # Store the entire webhook payload
            )
            if start_time:
                call.start_time = datetime.fromtimestamp(start_time / 1000)
            db.add(call)
            await db.commit()
            await db.refresh(call)
            logger.info(f"Created new call record: {call.id} for call_id: {search_call_id}")
        
        if call:
            # Update call based on state
            if call_state == "ringing":
                call.status = "ringing"
            elif call_state == "answered":
                call.status = "active"
            elif call_state == "ended":
                call.status = "ended"
                if end_time:
                    call.end_time = datetime.fromtimestamp(end_time / 1000)
                if answer_time and end_time:
                    duration = (end_time - answer_time) / 1000  # Convert to seconds
                    call.duration_seconds = int(duration)
            
            # Update raw_data with latest webhook data
            if call.raw_data:
                # Merge with existing data
                call.raw_data = {**call.raw_data, **data}
            else:
                call.raw_data = data
            
            await db.commit()
            
            result = {
                "status": "success", 
                "call_id": str(call.id),
                "call_status": call.status
            }
        
        # Broadcast status update to WebSocket clients
        if result["status"] == "success":
            await websocket_manager.broadcast_to_call(
                result["call_id"],
                {
                    "event": "call:status",
                    "data": {
                        "call_id": result["call_id"],
                        "status": result["call_status"],
                        "call_state": call_state
                    }
                }
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing call state: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}


@router.post("/recording-status")
async def handle_recording_status(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle recording status updates from SignalWire"""
    
    try:
        data = await request.json()
        logger.info("="*80)
        logger.info("RECORDING STATUS WEBHOOK RECEIVED")
        logger.info("="*80)
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Full payload: {json.dumps(data, indent=2)}")
        
        # Extract fields from the correct structure
        params = data.get("params", {})
        
        # Extract recording details
        recording_id = params.get("recording_id", "")
        call_id = params.get("call_id", "")
        state = params.get("state", "")
        url = params.get("url", "")
        
        # Extract record object details
        record = params.get("record", {})
        audio = record.get("audio", {})
        format = audio.get("format", "mp3")
        stereo = audio.get("stereo", False)
        direction = audio.get("direction", "both")
        
        # Log specific fields for database mapping
        logger.info("Extracted fields for database:")
        logger.info(f"  - call_id: {call_id}")
        logger.info(f"  - recording_id: {recording_id}")
        logger.info(f"  - state: {state}")
        logger.info(f"  - url: {url}")
        logger.info(f"  - format: {format}")
        logger.info(f"  - stereo: {stereo}")
        logger.info(f"  - direction: {direction}")
        logger.info("="*80)
        
        # Process recording status
        if state == "recording" and call_id:
            # Find the call in database
            from sqlalchemy import select
            from models import Call, Recording
            
            result = await db.execute(
                select(Call).where(Call.signalwire_call_id == call_id)
            )
            call = result.scalar_one_or_none()
            
            if call and recording_id:
                # Check if recording already exists
                result = await db.execute(
                    select(Recording).where(Recording.recording_id == recording_id)
                )
                recording = result.scalar_one_or_none()
                
                if not recording:
                    # Create new recording record
                    recording = Recording(
                        call_id=call.id,
                        recording_id=recording_id,
                        url=url,
                        format=format,
                        stereo=stereo,
                        direction=direction,
                        state=state,
                        raw_data=data  # Store the entire webhook payload
                    )
                    db.add(recording)
                    await db.commit()
                    await db.refresh(recording)
                    logger.info(f"Created recording record: {recording.id} for call {call.id}")
                
                # Broadcast recording availability to WebSocket clients
                await websocket_manager.broadcast_to_call(
                    str(call.id),
                    {
                        "event": "recording:available",
                        "data": {
                            "call_id": str(call.id),
                            "recording_id": str(recording.id),
                            "recording_url": url,
                            "format": format
                        }
                    }
                )
            else:
                logger.warning(f"Recording received for unknown call: {call_id}")
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Error processing recording status: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}