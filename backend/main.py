from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging

from api.endpoints import auth, calls, documents, webhooks
from websocket.handlers import websocket_endpoint
from core.config import settings
from core.database import engine
from models import Base

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting LiveCall API...")
    # Create database tables
    async with engine.begin() as conn:
        from sqlalchemy import MetaData
        await conn.run_sync(Base.metadata.create_all)
    
    # Run database migrations
    try:
        from run_migrations import run_all_migrations
        logger.info("Running database migrations...")
        await run_all_migrations()
    except Exception as e:
        logger.warning(f"Could not run migrations: {e}")
    
    # Initialize demo data (including demo user)
    try:
        from init_demo import init_database
        logger.info("Initializing demo data...")
        await init_database()
    except Exception as e:
        logger.warning(f"Could not initialize demo data: {e}")
    
    yield
    # Shutdown
    logger.info("Shutting down LiveCall API...")


app = FastAPI(
    title="LiveCall API",
    description="Real-time call assistance system",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3030",
    "http://localhost",
]

# Add public URL if configured
if settings.public_url:
    allowed_origins.append(settings.public_url)
    # Also add https version if it's an ngrok URL
    if "ngrok" in settings.public_url:
        allowed_origins.append(settings.public_url.replace("http://", "https://"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(auth.router)
app.include_router(calls.router)
app.include_router(documents.router)
app.include_router(webhooks.router)

# WebSocket endpoint
app.websocket("/ws")(websocket_endpoint)


@app.get("/")
async def root():
    return {
        "message": "LiveCall API is running",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.environment
    }


@app.get("/api/settings")
async def get_settings():
    """Get public settings for frontend"""
    return {
        "listening_modes": ["agent", "customer", "both"],
        "features": {
            "transcription": True,
            "ai_suggestions": True,
            "call_summary": True,
            "document_search": True
        }
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)