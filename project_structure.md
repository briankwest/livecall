# Project Structure

```
livecall/
├── backend/
│   ├── api/
│   │   ├── endpoints/
│   │   │   ├── auth.py
│   │   │   ├── calls.py
│   │   │   ├── documents.py
│   │   │   └── webhooks.py
│   │   ├── middleware/
│   │   │   ├── auth.py
│   │   │   └── cors.py
│   │   └── websocket/
│   │       ├── events.py
│   │       └── handlers.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/
│   │   ├── call.py
│   │   ├── transcription.py
│   │   └── document.py
│   ├── services/
│   │   ├── signalwire.py
│   │   ├── openai_service.py
│   │   ├── vector_db.py
│   │   └── call_processor.py
│   ├── utils/
│   │   ├── embeddings.py
│   │   └── text_processing.py
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   ├── call/
│   │   │   └── layout/
│   │   ├── contexts/
│   │   │   ├── WebSocketContext.tsx
│   │   │   ├── CallContext.tsx
│   │   │   └── UserContext.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── LiveCall.tsx
│   │   │   └── CallHistory.tsx
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts
│   │   │   └── useCall.ts
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── App.tsx
│   │   └── index.tsx
│   ├── package.json
│   └── tsconfig.json
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
├── scripts/
│   ├── init_db.py
│   ├── ingest_documents.py
│   └── test_signalwire.py
├── docs/
│   ├── architecture.md
│   ├── api_endpoints.md
│   └── deployment.md
├── .env.example
├── .gitignore
└── README.md
```

## Key Dependencies

### Backend (Python)
```txt
fastapi==0.104.0
uvicorn==0.24.0
python-socketio==5.10.0
sqlalchemy==2.0.23
asyncpg==0.29.0
redis==5.0.1
openai==1.3.0
pinecone-client==2.2.4
pydantic==2.5.0
python-jose==3.3.0
httpx==0.25.0
```

### Frontend (React)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "socket.io-client": "^4.6.0",
    "axios": "^1.6.0",
    "@tanstack/react-query": "^5.0.0",
    "@mui/material": "^5.14.0",
    "react-pdf": "^7.5.0",
    "date-fns": "^2.30.0"
  }
}
```