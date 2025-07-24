from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@postgres:5432/livecall"
    
    # Redis
    redis_url: str = "redis://redis:6379"
    
    # Security
    secret_key: str = "your-secret-key-here"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # SignalWire
    signalwire_project_id: Optional[str] = None
    signalwire_token: Optional[str] = None
    signalwire_space_url: Optional[str] = None
    signalwire_phone_number: Optional[str] = None
    signalwire_from_number: Optional[str] = None
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"
    embedding_model: str = "text-embedding-ada-002"
    
    # Application
    environment: str = "development"
    log_level: str = "INFO"
    public_url: str = "http://localhost:3030"
    
    # Vector DB
    vector_dimensions: int = 1536
    
    # Rate limiting
    rate_limit_per_minute: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()