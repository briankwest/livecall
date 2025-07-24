# WebSocket Architecture

## Overview
Real-time bidirectional communication between backend and React frontend for live call assistance.

## WebSocket Events

### 1. Client → Server Events
```typescript
// Connection
{
  "event": "agent:connect",
  "data": {
    "agent_id": "agent_123",
    "auth_token": "jwt_token"
  }
}

// Subscribe to call
{
  "event": "call:subscribe",
  "data": {
    "call_id": "call_xxx"
  }
}

// Agent feedback
{
  "event": "doc:feedback",
  "data": {
    "doc_id": "doc_123",
    "helpful": true,
    "call_id": "call_xxx"
  }
}
```

### 2. Server → Client Events
```typescript
// Live transcription
{
  "event": "transcription:update",
  "data": {
    "call_id": "call_xxx",
    "speaker": "customer",
    "text": "I'm having trouble with...",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}

// AI suggestions
{
  "event": "ai:suggestion",
  "data": {
    "call_id": "call_xxx",
    "documents": [
      {
        "id": "doc_123",
        "title": "Troubleshooting Guide",
        "excerpt": "...",
        "relevance": 0.92
      }
    ],
    "summary": "Customer experiencing login issues"
  }
}

// Call status
{
  "event": "call:status",
  "data": {
    "call_id": "call_xxx",
    "status": "ended",
    "duration": 300
  }
}
```

## Implementation Details

### Backend (FastAPI + Socket.io)
```python
# Key components
- Authentication middleware
- Room-based isolation (one room per call)
- Redis pub/sub for scaling
- Connection pool management
- Heartbeat/reconnection logic
```

### Frontend (React + Socket.io Client)
```typescript
// Key features
- Auto-reconnection with exponential backoff
- Event queueing during disconnection
- React Context for global socket state
- Custom hooks for event subscriptions
- Optimistic UI updates
```

## Scaling Considerations
1. **Horizontal scaling**: Use Redis adapter for Socket.io
2. **Load balancing**: Sticky sessions for WebSocket connections
3. **Connection limits**: Max 1000 concurrent connections per server
4. **Message throttling**: Rate limit client events