from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import logging
import json
from datetime import datetime, timezone
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
    
    logger.info("=" * 80)
    logger.info("📥 WEBHOOK: /signalwire/transcribe")
    logger.info("=" * 80)
    
    # Get raw body for signature verification
    body = await request.body()
    
    # Verify webhook signature
    signalwire_service = SignalWireService()
    signature = request.headers.get("X-SignalWire-Signature", "")
    
    if not signalwire_service.verify_webhook_signature(signature, body):
        logger.warning("❌ Invalid webhook signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    # Parse JSON data
    data = await request.json()
    
    # Log the full webhook payload
    logger.info("📋 Headers:")
    for key, value in request.headers.items():
        if key.lower() not in ['authorization', 'x-api-key', 'cookie', 'x-signalwire-signature']:
            logger.info(f"  {key}: {value}")
    
    logger.info("📦 Body:")
    logger.info(json.dumps(data, indent=2))
    logger.info("-" * 80)
    
    # Handle transcription event
    result = await signalwire_service.handle_transcription_event(data, db)
    
    # If transcription was created, process it SYNCHRONOUSLY for now
    if result["status"] == "success":
        logger.info(f"🎯 Triggering vector search for transcription {result['transcription_id']}")
        call_processor = CallProcessor()
        # Make it synchronous to ensure it runs
        await call_processor.process_transcription(
            result["transcription_id"],
            result["call_id"],
            db
        )
        logger.info(f"✅ Vector search completed for transcription {result['transcription_id']}")
        
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
    
    # ALWAYS check query parameters first (for both GET and POST)
    # This is important because SignalWire may send POST with query params
    direction = request.query_params.get("direction", "outbound")
    username = request.query_params.get("username", "")  # Get username for inbound calls
    
    # Override with query params if they exist
    if request.query_params.get("destination_number"):
        destination_number = request.query_params.get("destination_number", "")
    
    logger.info(f"Query params: {dict(request.query_params)}")
    
    # Try to get additional parameters from body/form data
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
            
            # Check for direction (only override if not already set from query params)
            if not request.query_params.get("direction"):
                direction = form_data.get("direction", direction)
                
        except:
            # Try JSON body
            try:
                body = await request.json()
                logger.info(f"JSON body: {body}")
                user_vars = body.get("userVariables", body)
                if not destination_number:
                    destination_number = user_vars.get("destination_number", "")
                # Only override direction if not set from query params
                if not request.query_params.get("direction"):
                    direction = body.get("direction", user_vars.get("direction", direction))
            except:
                pass
    
    # Use the base URL from settings
    base_url = settings.public_url
    
    if not destination_number and direction == "outbound":
        logger.error("No destination number provided in request")
        # For testing, use a default number
        destination_number = "+19184238080"  # Default test number
    
    logger.info(f"Generating SWML for {direction} call")
    logger.info(f"  destination_number: {destination_number}")
    logger.info(f"  from_number: {from_number}")
    logger.info(f"  username: {username}")
    logger.info(f"  Base URL: {base_url}")
    
    # Set transcription direction based on call direction
    # For outbound: remote-caller first (customer), then local-caller (agent)
    # For inbound: local-caller first (agent), then remote-caller (customer)
    transcription_direction = ["remote-caller", "local-caller"] if direction == "outbound" else ["local-caller", "remote-caller"]
    
    # Build the complete SWML response using userVariables
    # For inbound calls, remove "from" and set "to" as /private/username
    if direction == "inbound" and username:
        connect_config = {
            "to": f"/private/{username}",
            "timeout": 30,
            "call_state_events": ["created", "ringing", "answered", "ended"],
            "call_state_url": f"{base_url}/api/webhooks/call-state"
        }
        logger.info(f"Inbound call configuration - routing to: /private/{username}")
    else:
        # Outbound call configuration
        connect_config = {
            "to": "%{vars.userVariables.destination_number}",
            "from": "%{vars.userVariables.from_number}",
            "timeout": 30,
            "call_state_events": ["created", "ringing", "answered", "ended"],
            "call_state_url": f"{base_url}/api/webhooks/call-state"
        }
        logger.info(f"Outbound call configuration - to: {destination_number}, from: {from_number}")
    
    # Build SWML sections
    main_sections = [
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
                        "direction": transcription_direction
                    }
                }
            }
        },
        {
            "connect": connect_config
        }
    ]
    
    # For outbound calls, userVariables come from the client dial command
    # For inbound calls, we need to set them in SWML
    if direction == "inbound":
        # Add set command at the beginning for inbound calls
        main_sections_with_set = [
            {
                "set": {
                    "direction": "inbound",
                    "username": username
                }
            }
        ] + main_sections
        
        swml_response = {
            "version": "1.0.0",
            "sections": {
                "main": main_sections_with_set
            }
        }
    else:
        # Outbound - userVariables come from client.dial()
        swml_response = {
            "version": "1.0.0",
            "sections": {
                "main": main_sections
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
    
    logger.info("=" * 80)
    logger.info("📥 WEBHOOK: /transcription")
    logger.info("=" * 80)
    
    try:
        data = await request.json()
        
        # Log headers
        logger.info("📋 Headers:")
        for key, value in request.headers.items():
            if key.lower() not in ['authorization', 'x-api-key', 'cookie']:
                logger.info(f"  {key}: {value}")
        
        # Log body
        logger.info("📦 Body:")
        logger.info(json.dumps(data, indent=2))
        logger.info("-" * 80)
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Full payload: {json.dumps(data, indent=2)}")
        
        # Extract transcription details from SignalWire format
        utterance = data.get("utterance", {})
        text = utterance.get("content", "")
        speaker = utterance.get("role", "unknown")
        # Confidence is at top level, not in utterance
        confidence = data.get("confidence", 1.0)
        
        # Log the raw utterance data to debug speaker role
        logger.info(f"Raw utterance data: {json.dumps(utterance, indent=2)}")
        
        # Get call info
        call_info = data.get("call_info", {})
        call_id = call_info.get("call_id", "")
        
        # Get timestamp from utterance
        timestamp = utterance.get("timestamp", 0)
        
        # Get channel data for user variables (destination number, etc)
        channel_data = data.get("channel_data", {})
        swml_vars = channel_data.get("SWMLVars", {})
        # For outbound calls, variables are under userVariables
        # For inbound calls with set command, they're at the top level of SWMLVars
        user_vars = swml_vars.get("userVariables", {})
        
        # Also check top-level SWML vars (for inbound calls using set command)
        if not user_vars:
            user_vars = swml_vars
        
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
        logger.info(f"  - direction from user_vars: {user_vars.get('direction', 'NOT PROVIDED')}")
        logger.info("="*80)
        
        # Skip empty transcriptions
        if not text.strip():
            return {"status": "ignored", "reason": "empty transcription"}
        
        # Map speaker role to our format based on call direction
        # For outbound calls: local-caller = agent, remote-caller = customer
        # For inbound calls: remote-caller = customer, local-caller = agent
        # Default to outbound mapping if direction is not set
        speaker_mapped = speaker  # Default fallback
        
        # Get or create call record
        from sqlalchemy import select, or_
        from models import Call, Transcription
        
        # First check if there's a call with this ID
        result = await db.execute(
            select(Call).where(Call.signalwire_call_id == call_id)
        )
        call = result.scalar_one_or_none()
        
        # If not found, try finding by checking if any call's raw_data contains this call_id
        # This handles the case where transcriptions come from the PSTN leg
        if not call:
            # Simple approach: check all active calls
            result = await db.execute(
                select(Call).where(Call.status == "active").order_by(Call.created_at.desc()).limit(1)
            )
            call = result.scalar_one_or_none()
            
            if call:
                logger.info(f"Found active call {call.id} for transcription from call_id {call_id}")
        
        if not call:
            # Create new call record
            # Try to determine direction from user variables or default to outbound
            call_direction = user_vars.get("direction", "outbound")
            # Get agent username from variables
            agent_username = user_vars.get("username", "") or user_vars.get("agent_id", "")
            
            call = Call(
                signalwire_call_id=call_id,
                phone_number=user_vars.get("destination_number", "Unknown"),
                agent_id=agent_username,  # Store the agent username
                status="active",
                listening_mode="both",
                direction=call_direction,
                raw_data=data  # Store the entire webhook payload
            )
            db.add(call)
            await db.commit()
            await db.refresh(call)
            logger.info(f"Created new call record: {call.id} with direction: {call_direction} and agent: {agent_username}")
        else:
            # If call exists but direction or agent_id is not set, update from user variables
            updated = False
            if not call.direction or call.direction == "":
                call_direction = user_vars.get("direction", "outbound")
                call.direction = call_direction
                updated = True
            
            if not call.agent_id or call.agent_id == "":
                agent_username = user_vars.get("username", "") or user_vars.get("agent_id", "")
                if agent_username:
                    call.agent_id = agent_username
                    updated = True
            
            if updated:
                await db.commit()
                logger.info(f"Updated existing call {call.id} with direction: {call.direction} and agent: {call.agent_id}")
        
        # Now map speaker based on call direction
        logger.info(f"Call direction from database: {call.direction}")
        logger.info(f"Original speaker role from webhook: {speaker}")
        
        if call.direction == "outbound":
            # Outbound: remote-caller = agent (you), local-caller = customer (person you called)
            # This is because SignalWire considers the PSTN leg as "local" in the context of SWML
            if speaker == "remote-caller":
                speaker_mapped = "agent"
            elif speaker == "local-caller":
                speaker_mapped = "customer"
            else:
                speaker_mapped = speaker  # fallback
                logger.warning(f"Unknown speaker role for outbound call: {speaker}")
        else:  # inbound
            # Inbound: local-caller = agent, remote-caller = customer
            # This is the expected mapping for inbound calls
            if speaker == "local-caller":
                speaker_mapped = "agent"
            elif speaker == "remote-caller":
                speaker_mapped = "customer"
            else:
                speaker_mapped = speaker  # fallback
                logger.warning(f"Unknown speaker role for inbound call: {speaker}")
        
        logger.info(f"FINAL Speaker mapping: {speaker} -> {speaker_mapped} (call direction: {call.direction})")
        
        # Analyze sentiment for both customer and agent messages
        sentiment = "neutral"
        sentiment_score = 0.5
        
        if text.strip():
            try:
                # Simple sentiment analysis based on keywords for now
                text_lower = text.lower()
                
                # Different word lists for customer vs agent
                if speaker_mapped == "customer":
                    # Customer sentiment indicators
                    negative_words = ['frustrated', 'angry', 'mad', 'terrible', 'awful', 'worst', 'hate', 'stupid', 'useless', 'broken', 'not working', 'doesn\'t work', 'unacceptable', 'ridiculous', 'disappointed']
                    positive_words = ['thank', 'thanks', 'great', 'excellent', 'wonderful', 'perfect', 'awesome', 'happy', 'love', 'appreciate', 'helpful', 'satisfied', 'pleased']
                else:  # agent
                    # Agent sentiment indicators (professional language)
                    negative_words = ['apologize', 'sorry', 'unfortunately', 'unable', 'cannot', 'issue', 'problem', 'delay', 'inconvenience', 'difficult']
                    positive_words = ['certainly', 'absolutely', 'happy to help', 'glad', 'excellent', 'perfect', 'resolved', 'solution', 'assist', 'help you', 'my pleasure']
                
                negative_count = sum(1 for word in negative_words if word in text_lower)
                positive_count = sum(1 for word in positive_words if word in text_lower)
                
                if negative_count > positive_count:
                    sentiment = "negative"
                    sentiment_score = 0.2
                elif positive_count > negative_count:
                    sentiment = "positive"
                    sentiment_score = 0.8
                else:
                    sentiment = "neutral"
                    sentiment_score = 0.5
                    
                logger.info(f"Sentiment analysis for {speaker_mapped}: {sentiment} (score: {sentiment_score})")
            except Exception as e:
                logger.error(f"Error analyzing sentiment: {e}")
                # Continue with defaults if sentiment analysis fails
        
        # Create transcription record
        transcription = Transcription(
            call_id=call.id,
            speaker=speaker_mapped,
            text=text,
            confidence=confidence,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            timestamp=datetime.fromtimestamp(timestamp / 1000000, tz=timezone.utc) if timestamp else datetime.now(timezone.utc),  # Convert microseconds
            raw_data=data  # Store the entire webhook payload
        )
        db.add(transcription)
        await db.commit()
        await db.refresh(transcription)
        
        result = {"status": "success", "transcription_id": str(transcription.id), "call_id": str(call.id)}
        
        # If transcription was created, process it and broadcast via WebSocket
        if result["status"] == "success":
            # Process in background - create a new session for the background task
            from core.database import AsyncSessionLocal
            
            async def process_with_new_session(transcription_id: str, call_id: str):
                async with AsyncSessionLocal() as new_db:
                    try:
                        call_processor = CallProcessor()
                        await call_processor.process_transcription(
                            transcription_id,
                            call_id,
                            new_db
                        )
                    except Exception as e:
                        logger.error(f"Error in background transcription processing: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
            
            background_tasks.add_task(
                process_with_new_session,
                result["transcription_id"],
                result["call_id"]
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
                        "confidence": confidence,
                        "sentiment": sentiment,
                        "sentiment_score": sentiment_score
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
    
    logger.info("=" * 80)
    logger.info("📥 WEBHOOK: /call-state")
    logger.info("=" * 80)
    
    try:
        data = await request.json()
        
        # Log headers
        logger.info("📋 Headers:")
        for key, value in request.headers.items():
            if key.lower() not in ['authorization', 'x-api-key', 'cookie']:
                logger.info(f"  {key}: {value}")
        
        # Log body
        logger.info("📦 Body:")
        logger.info(json.dumps(data, indent=2))
        logger.info("-" * 80)
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
        
        # Also check channel_data for userVariables (like in transcription webhook)
        channel_data = data.get("channel_data", {})
        swml_vars = channel_data.get("SWMLVars", {})
        # For outbound calls, variables are under userVariables
        # For inbound calls with set command, they're at the top level of SWMLVars
        user_vars = swml_vars.get("userVariables", {})
        
        # Also check top-level SWML vars (for inbound calls using set command)
        if not user_vars:
            user_vars = swml_vars
        
        # If direction not in params, check variables
        if not direction and user_vars:
            direction = user_vars.get("direction", "outbound")
            logger.info(f"Got direction from SWML vars: {direction}")
        
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
        webrtc_call_id = parent.get("call_id") if parent else call_id
        pstn_call_id = call_id
        
        # Try to find existing call by either WebRTC or PSTN call ID
        result = await db.execute(
            select(Call).where(
                (Call.signalwire_call_id == webrtc_call_id) | 
                (Call.signalwire_call_id == pstn_call_id)
            )
        )
        call = result.scalar_one_or_none()
        
        if not call and call_state == "created":
            # Create new call record using WebRTC call ID as primary
            phone_number = device.get("params", {}).get("to_number") if device else "Unknown"
            # Get agent username from variables
            agent_username = user_vars.get("username", "") or user_vars.get("agent_id", "")
            
            call = Call(
                signalwire_call_id=webrtc_call_id,  # Use WebRTC call ID as primary
                phone_number=phone_number,
                agent_id=agent_username,  # Store the agent username
                status="active",
                listening_mode="both",
                direction=direction,  # Store call direction from params
                raw_data=data  # Store the entire webhook payload
            )
            if start_time:
                call.start_time = datetime.fromtimestamp(start_time / 1000)
            db.add(call)
            await db.commit()
            await db.refresh(call)
            logger.info(f"Created new call record: {call.id} for call_id: {webrtc_call_id} with agent: {agent_username}")
        
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
            
            # Update agent_id if missing
            if not call.agent_id or call.agent_id == "":
                agent_username = user_vars.get("username", "") or user_vars.get("agent_id", "")
                if agent_username:
                    call.agent_id = agent_username
                    logger.info(f"Updated call {call.id} with missing agent: {agent_username}")
            
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
            logger.info(f"Broadcasting call:status event for call {result['call_id']} with status: {result['call_status']}")
            status_message = {
                "event": "call:status",
                "data": {
                    "call_id": result["call_id"],
                    "status": result["call_status"],
                    "call_state": call_state
                }
            }
            
            # Broadcast to specific call connections
            await websocket_manager.broadcast_to_call(
                result["call_id"],
                status_message
            )
            
            # Also broadcast to general connections (for agents who haven't connected to specific call yet)
            await websocket_manager.broadcast_to_call(
                "general",
                status_message
            )
            
            logger.info(f"Broadcast complete for call {result['call_id']}")
        
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