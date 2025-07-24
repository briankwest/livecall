# LiveCall - Real-time Call Assistant

A real-time call assistance system that uses SignalWire for live transcription, OpenAI for intelligent processing, and vector databases for contextual documentation retrieval.

## Features

- **Live Call Transcription**: Real-time transcription using SignalWire's live_transcribe
- **AI-Powered Assistance**: OpenAI integration for intelligent conversation analysis
- **Vector Search**: Semantic search through documentation during calls
- **Configurable Listening**: Monitor agent-only, customer-only, or both sides
- **Real-time Dashboard**: React-based UI with WebSocket updates
- **Call Analytics**: Summaries, sentiment analysis, and action items

## Quick Start

1. **Clone and Initialize**
   ```bash
   git clone <repository>
   cd livecall
   make init
   ```

2. **Configure Environment**
   ```bash
   # Copy .env.example to .env and update with your credentials:
   - SignalWire credentials
   - OpenAI API key
   - Database passwords
   - Ngrok authtoken (for development)
   ```

3. **Start Services**
   ```bash
   # Production mode
   make up

   # Development mode with hot reload
   make dev
   ```

4. **Access Application**
   - Frontend: http://localhost:3030
   - API: http://localhost:3030/api
   - WebSocket: ws://localhost:3030/ws
   - PostgreSQL: localhost:5433 (external)
   - Redis: localhost:6380 (external)

## Development with Ngrok

For SignalWire webhooks in development, run ngrok separately:

```bash
# Install ngrok (https://ngrok.com/download)
# Then run:
ngrok http 80

# Update .env with the ngrok URL:
PUBLIC_URL=https://your-subdomain.ngrok-free.app

# Configure SignalWire webhook to:
# https://your-subdomain.ngrok-free.app/webhooks/signalwire/transcribe
```

## Architecture

- **Frontend**: React + TypeScript + Material-UI
- **Backend**: Python FastAPI + Socket.io
- **Database**: PostgreSQL + Redis
- **Vector DB**: Qdrant (dev) / Pinecone (prod)
- **Proxy**: Nginx reverse proxy

## Useful Commands

```bash
make build    # Build Docker images
make logs     # View logs
make shell    # Backend shell
make shell-db # PostgreSQL shell
make clean    # Remove all data
make status   # Check service status
```

## API Documentation

Once running, access interactive API docs at:
- Swagger UI: http://localhost/api/docs
- ReDoc: http://localhost/api/redoc

## Security Notes

- Currently configured for HTTP (port 80)
- SSL/TLS ready - update nginx config for production
- All sensitive data in environment variables
- JWT authentication for API endpoints

## Next Steps

1. Create backend application code (main.py, models, services)
2. Build React frontend components
3. Implement SignalWire webhook handlers
4. Set up vector database ingestion pipeline
5. Configure production SSL certificates