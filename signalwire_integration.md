# SignalWire Integration Flow

## Live Transcription Setup

### 1. SWML Configuration
```yaml
sections:
  main:
    - answer: {}
    - live_transcribe:
        action:
          start:
            webhook: "https://your-backend.com/webhooks/signalwire/transcribe"
            lang: en
            live_events: true
            ai_summary: true
            speech_timeout: 30
            vad_silence_ms: 500
            vad_thresh: 0.6
            debug_level: 2
            direction:
              - remote-caller
              - local-caller
            speech_engine: default
            summary_prompt: "Summarize this conversation"
```

### 2. Webhook Event Structure
```json
{
  "event": "transcription",
  "call_id": "call_xxx",
  "text": "transcribed text",
  "speaker": "inbound|outbound",
  "confidence": 0.95,
  "is_final": true,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 3. Backend Processing Flow
1. **Receive webhook** at `/webhooks/signalwire/transcribe`
2. **Validate** SignalWire signature
3. **Store** transcription in database
4. **Queue** for AI processing if buffer threshold met
5. **Broadcast** via WebSocket to connected clients

### 4. Listening Mode Configuration
- **Agent Only**: Filter events where speaker = "outbound"
- **Customer Only**: Filter events where speaker = "inbound"  
- **Both**: Process all transcription events

### 5. Event Buffering Strategy
- Collect transcriptions for 2-3 seconds
- Group by speaker for context
- Send to OpenAI when:
  - Silence detected (speech_complete)
  - Buffer size reaches threshold
  - Topic change detected