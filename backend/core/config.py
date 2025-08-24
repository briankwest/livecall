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
    
    # AWS Bedrock
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "amazon.nova-micro-v1:0"
    
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