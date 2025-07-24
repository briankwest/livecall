from typing import Dict, Set, Any
import json
import logging
from fastapi import WebSocket
from collections import defaultdict

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Store active connections by call_id
        self.active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        # Store connection metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        
    async def connect(self, websocket: WebSocket, call_id: str, agent_id: str):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections[call_id].add(websocket)
        self.connection_metadata[websocket] = {
            "call_id": call_id,
            "agent_id": agent_id
        }
        logger.info(f"Agent {agent_id} connected to call {call_id}")
        
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        metadata = self.connection_metadata.get(websocket, {})
        call_id = metadata.get("call_id")
        agent_id = metadata.get("agent_id")
        
        if call_id and websocket in self.active_connections[call_id]:
            self.active_connections[call_id].remove(websocket)
            if not self.active_connections[call_id]:
                del self.active_connections[call_id]
                
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]
            
        logger.info(f"Agent {agent_id} disconnected from call {call_id}")
        
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send message to specific WebSocket connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
            
    async def broadcast_to_call(self, call_id: str, message: Dict[str, Any]):
        """Broadcast message to all connections for a specific call"""
        logger.info(f"Broadcasting to call {call_id}: {message.get('event', 'unknown event')}")
        if call_id in self.active_connections:
            logger.info(f"Found {len(self.active_connections[call_id])} connections for call {call_id}")
            disconnected = []
            for connection in self.active_connections[call_id]:
                try:
                    await connection.send_json(message)
                    logger.info(f"Message sent to connection for call {call_id}")
                except Exception as e:
                    logger.error(f"Error broadcasting to connection: {e}")
                    disconnected.append(connection)
                    
            # Clean up disconnected connections
            for connection in disconnected:
                self.disconnect(connection)
        else:
            logger.warning(f"No active connections found for call {call_id}")
                
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast message to all active connections"""
        all_connections = set()
        for connections in self.active_connections.values():
            all_connections.update(connections)
            
        disconnected = []
        for connection in all_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to all: {e}")
                disconnected.append(connection)
                
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
            
    def get_call_connections(self, call_id: str) -> int:
        """Get number of active connections for a call"""
        return len(self.active_connections.get(call_id, set()))
    
    def get_all_active_calls(self) -> list[str]:
        """Get list of all active call IDs"""
        return list(self.active_connections.keys())
    
    async def broadcast_to_user(self, agent_id: str, message: Dict[str, Any]):
        """Broadcast message to all connections for a specific user"""
        disconnected = []
        for websocket, metadata in self.connection_metadata.items():
            if metadata.get("agent_id") == agent_id:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to user: {e}")
                    disconnected.append(websocket)
                    
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)


# Global WebSocket manager instance
websocket_manager = ConnectionManager()