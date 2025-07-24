from fastapi import WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging
import json
from core.database import get_db
from core.security import verify_token
from .manager import websocket_manager

logger = logging.getLogger(__name__)


async def websocket_endpoint(
    websocket: WebSocket,
    call_id: Optional[str] = Query(None),
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for real-time call updates"""
    
    # Verify authentication token
    try:
        payload = verify_token(token)
        agent_id = payload.get("sub")
    except Exception as e:
        logger.error(f"WebSocket auth failed: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
        return
    
    # Connect to WebSocket (use 'general' as call_id if none provided)
    connection_call_id = call_id or "general"
    await websocket_manager.connect(websocket, connection_call_id, agent_id)
    
    try:
        # Send initial connection success message
        await websocket_manager.send_personal_message(
            {
                "event": "connection:success",
                "data": {
                    "call_id": call_id,
                    "agent_id": agent_id,
                    "message": "Connected to real-time updates" if call_id else "Connected to general updates"
                }
            },
            websocket
        )
        
        # Listen for messages from client
        while True:
            data = await websocket.receive_json()
            await handle_client_message(websocket, data, call_id, agent_id, db)
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)


async def handle_client_message(
    websocket: WebSocket,
    data: dict,
    call_id: str,
    agent_id: str,
    db: AsyncSession
):
    """Handle messages from WebSocket client"""
    
    event = data.get("event")
    event_data = data.get("data", {})
    
    logger.info(f"Received WebSocket message: {event} from agent {agent_id}")
    
    if event == "ping":
        # Respond to ping
        await websocket_manager.send_personal_message(
            {"event": "pong", "data": {"timestamp": event_data.get("timestamp")}},
            websocket
        )
        
    elif event == "doc:feedback":
        # Handle document feedback
        doc_id = event_data.get("doc_id")
        helpful = event_data.get("helpful")
        # TODO: Store feedback in database
        await websocket_manager.send_personal_message(
            {"event": "feedback:received", "data": {"doc_id": doc_id}},
            websocket
        )
        
    elif event == "call:request_summary":
        # Request call summary generation
        # TODO: Trigger summary generation
        await websocket_manager.send_personal_message(
            {"event": "summary:generating", "data": {"call_id": call_id}},
            websocket
        )
        
    else:
        logger.warning(f"Unknown WebSocket event: {event}")