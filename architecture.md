# Live Call Assistant Architecture

## Overview
Real-time call assistance system using SignalWire for live transcription, OpenAI for intelligent processing, and vector databases for contextual documentation retrieval.

## Tech Stack
- **Backend**: Python (FastAPI)
- **Frontend**: React + TypeScript
- **Real-time**: WebSockets (Socket.io)
- **Databases**: 
  - PostgreSQL (call data, summaries)
  - Redis (caching, pub/sub)
  - Pinecone/Weaviate (vector embeddings)
- **External Services**:
  - SignalWire (telephony, transcription)
  - OpenAI (LLM processing)

## Data Flow
1. SignalWire sends live transcription events via webhooks
2. Backend processes transcription in real-time
3. OpenAI analyzes conversation context
4. Vector database searched for relevant documentation
5. Results pushed to agent via WebSocket
6. Frontend displays assistance in real-time

## Key Features
- Configurable listening modes (agent-only, customer-only, both)
- Real-time documentation suggestions
- Call summarization and storage
- Historical analysis capabilities