# SignalWire Webhook Implementation

## Overview
This document describes the webhook handlers implemented for SignalWire integration in the LiveCall system.

## Webhook Endpoints

### 1. Transcription Webhook (`/api/webhooks/transcription`)
Handles real-time transcription events from SignalWire.

**Data Structure:**
```json
{
  "utterance": {
    "role": "remote-caller|local-caller",
    "content": "transcribed text",
    "confidence": 0.95,
    "timestamp": 1234567890
  },
  "call_info": {
    "call_id": "signalwire-call-id"
  },
  "channel_data": {
    "SWMLVars": {
      "userVariables": {
        "destination_number": "+1234567890",
        "from_number": "+0987654321"
      }
    }
  }
}
```

**Processing:**
- Extracts transcription from `utterance.content`
- Maps speaker roles: `remote-caller` → `customer`, `local-caller` → `agent`
- Creates/updates call record in database
- Stores transcription with speaker identification
- Broadcasts to WebSocket clients
- Triggers AI processing for document search

### 2. Call State Webhook (`/api/webhooks/call-state`)
Handles call lifecycle events (created, ringing, answered, ended).

**Data Structure:**
```json
{
  "params": {
    "call_id": "signalwire-call-id",
    "call_state": "created|ringing|answered|ended",
    "device": {
      "params": {
        "from_number": "+1234567890",
        "to_number": "+0987654321"
      }
    },
    "start_time": 1234567890000,
    "answer_time": 1234567890000,
    "end_time": 1234567890000
  }
}
```

**Processing:**
- Creates call record on first event
- Updates call status throughout lifecycle
- Calculates call duration on completion
- Stores phone numbers and timing information
- Broadcasts status updates via WebSocket

### 3. Recording Status Webhook (`/api/webhooks/recording-status`)
Handles recording completion events.

**Data Structure:**
```json
{
  "params": {
    "recording_id": "rec-123",
    "call_id": "signalwire-call-id",
    "state": "completed",
    "url": "https://recording-url.mp3",
    "record": {
      "audio": {
        "duration": 120.5,
        "size": 2048000,
        "channels": 2,
        "codec": "mp3"
      }
    }
  }
}
```

**Processing:**
- Logs recording completion
- Stores recording URL (future: download and store)
- Broadcasts recording availability to clients

## Database Schema

### Call Model
- `signalwire_call_id`: Unique SignalWire identifier
- `phone_number`: Customer's phone number
- `start_time`: Call start timestamp
- `end_time`: Call end timestamp
- `duration_seconds`: Calculated duration
- `status`: active|ended|failed
- `listening_mode`: both|agent|customer

### Transcription Model
- `call_id`: Foreign key to Call
- `speaker`: agent|customer
- `text`: Transcribed content
- `confidence`: Recognition confidence score
- `timestamp`: When transcription occurred

## WebSocket Events

### `transcription:update`
```json
{
  "event": "transcription:update",
  "data": {
    "call_id": "uuid",
    "transcription_id": "uuid",
    "speaker": "agent|customer",
    "text": "transcribed text",
    "timestamp": 1234567890
  }
}
```

### `call:status`
```json
{
  "event": "call:status",
  "data": {
    "call_id": "uuid",
    "status": "active|ended|failed",
    "call_state": "created|ringing|answered|ended"
  }
}
```

### `recording:available`
```json
{
  "event": "recording:available",
  "data": {
    "call_id": "uuid",
    "recording_url": "https://...",
    "duration": 120.5,
    "size": 2048000
  }
}
```

## Testing

Use the test script to verify webhook functionality:
```bash
cd backend
python scripts/test_webhooks.py
```

This will send sample webhook payloads to each endpoint and verify the responses.

## Future Enhancements

1. **Recording Management**
   - Download and store recordings locally
   - Implement recording playback API
   - Add recording transcription

2. **Enhanced Call Tracking**
   - Support for parent/child call relationships
   - Track WebRTC to PSTN call mapping
   - Store additional metadata (quality scores, etc.)

3. **Real-time Analytics**
   - Call duration tracking
   - Speaker time analysis
   - Sentiment scoring per utterance

4. **Security**
   - Implement webhook signature verification
   - Add rate limiting for webhook endpoints
   - Audit logging for all webhook events