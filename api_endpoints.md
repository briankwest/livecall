# API Endpoints and Data Flow

## REST API Endpoints

### Authentication
```
POST   /api/auth/login
POST   /api/auth/logout
POST   /api/auth/refresh
GET    /api/auth/me
```

### Calls Management
```
GET    /api/calls                 # List calls with pagination
GET    /api/calls/:id             # Get call details
POST   /api/calls/:id/end         # End active call
GET    /api/calls/:id/summary     # Get call summary
GET    /api/calls/:id/transcripts # Get full transcription
```

### Documents/Knowledge Base
```
POST   /api/documents             # Upload new document
GET    /api/documents             # List documents
GET    /api/documents/:id         # Get document content
DELETE /api/documents/:id         # Remove document
POST   /api/documents/reindex     # Trigger reindexing
```

### Settings
```
GET    /api/settings              # Get user settings
PATCH  /api/settings              # Update settings
GET    /api/settings/listening-modes  # Available modes
```

### Webhooks (External)
```
POST   /webhooks/signalwire/transcribe  # SignalWire events
POST   /webhooks/signalwire/status     # Call status updates
```

## Data Flow Diagram

```
1. Call Initiation
   SignalWire → POST /webhooks/signalwire/status
   → Create call record in DB
   → Emit WebSocket event to agents

2. Live Transcription
   SignalWire → POST /webhooks/signalwire/transcribe
   → Store in DB
   → Buffer transcriptions
   → Process with OpenAI
   → Search vector DB
   → Emit suggestions via WebSocket

3. Document Retrieval
   AI Service → Vector DB query
   → Rank results
   → Format for display
   → Cache frequently accessed
   → Send to frontend

4. Call Completion
   SignalWire → Call ended event
   → Generate summary with OpenAI
   → Store in DB
   → Update analytics
   → Notify frontend
```

## Request/Response Examples

### Get Call Details
```json
// GET /api/calls/123
{
  "id": "123",
  "phone_number": "+1234567890",
  "agent_id": "agent_001",
  "start_time": "2024-01-01T10:00:00Z",
  "duration_seconds": 300,
  "status": "completed",
  "summary": "Customer inquiry about billing",
  "transcription_count": 45,
  "documents_accessed": 3
}
```

### WebSocket AI Suggestion
```json
{
  "event": "ai:suggestion",
  "data": {
    "context": "Customer asking about refund policy",
    "suggestions": [
      {
        "doc_id": "refund_policy_v2",
        "title": "Refund Policy Guidelines",
        "relevance": 0.94,
        "excerpt": "Refunds are processed within..."
      }
    ]
  }
}
```