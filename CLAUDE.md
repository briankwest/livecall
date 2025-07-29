# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend Development
```bash
# Run backend tests
make test

# Format Python code
docker-compose exec backend black .
docker-compose exec backend ruff check --fix .

# Access backend shell
make shell

# Database shell
make shell-db

# Run database migrations
make migrate
```

### Frontend Development
```bash
# Run frontend in development mode
cd frontend && npm run dev

# Build frontend
cd frontend && npm run build

# Lint and format TypeScript/React code
cd frontend && npm run lint
cd frontend && npm run format
```

### Docker Operations
```bash
# Start all services (production mode)
make up

# Start in development mode with hot reload
make dev

# View logs
make logs

# Check service status
make status

# Clean all data and volumes
make clean

# Restart services
make restart
```

## Architecture Overview

The LiveCall system is a real-time call assistance platform with the following key components:

### Backend (FastAPI + Python)
- **Entry Point**: `backend/main.py` - FastAPI application with Socket.io integration
- **API Structure**: RESTful endpoints organized in `backend/api/endpoints/` (auth, calls, documents, webhooks)
- **Real-time**: WebSocket handlers in `backend/websocket/` for live transcription and AI assistance
- **Services**: Core business logic in `backend/services/` including:
  - `signalwire_service.py`: SignalWire telephony integration
  - `openai_service.py`: OpenAI API integration for AI processing
  - `vector_search.py`: Semantic search implementation
  - `call_processor.py`: Real-time call processing pipeline
  - `sentiment_service.py`: Sentiment analysis for transcriptions
- **Models**: SQLAlchemy models in `backend/models/` for database entities
- **Database Migrations**: Alembic migrations in `backend/alembic/versions/` and custom migrations in `backend/migrations/`

### Frontend (React + TypeScript + Vite)
- **Entry Point**: `frontend/src/main.tsx`
- **Routing**: React Router v6 with authentication guards
- **State Management**: React Query (TanStack Query) for server state, Context API for auth
- **Real-time**: Socket.io client integration via custom hook `useWebSocket.ts`
- **UI Components**: Material-UI based components in `frontend/src/components/`
- **Key Pages**: Dashboard, LiveCall (real-time assistance), NewCall (initiate calls)
- **Form Handling**: React Hook Form for form validation and submission

### Infrastructure
- **Reverse Proxy**: Nginx configuration in `nginx/` handles routing between frontend and backend
- **Databases**: 
  - PostgreSQL with pgvector extension (port 5433 external) for persistent data and vector embeddings
  - Redis (port 6380 external) for caching and pub/sub
  - Vector DB (Qdrant dev / Pinecone prod) for semantic search
- **Docker**: Multi-container setup with separate dev/prod configurations
- **Ports**:
  - Frontend/Nginx: 3030 (HTTP), 3443 (HTTPS)
  - Backend API: 8000 (internal)
  - WebSocket: /ws endpoint

### Data Flow
1. SignalWire webhooks → `/webhooks/signalwire/transcribe` endpoint
2. Backend processes transcription → OpenAI for analysis
3. Vector search for relevant documentation
4. Results pushed via WebSocket to connected frontend clients
5. Frontend displays real-time assistance to agents

### Development Workflow
- Development uses `docker-compose.dev.yml` for hot reloading
- Frontend runs on Vite dev server (port 5173 internal, proxied through Nginx)
- Backend auto-reloads on code changes via uvicorn --reload
- For SignalWire integration, use ngrok for webhook forwarding (see docs/ngrok-setup.md)
- Demo user credentials: demo@livecall.ai / demo123 (created on startup via init_demo.py)