from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
from datetime import timedelta
from core.database import get_db
from core.security import verify_password, create_access_token, get_password_hash, get_current_user
from core.config import settings
from models import User
from pydantic import BaseModel, EmailStr
import httpx
import base64
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: str
    is_active: bool
    is_admin: bool


class Token(BaseModel):
    access_token: str
    token_type: str


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    
    # Check if user already exists
    result = await db.execute(
        select(User).where(
            (User.email == user_data.email) | (User.username == user_data.username)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        is_active=True,
        is_admin=False
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        is_admin=user.is_admin
    )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Login and receive access token"""
    
    # Find user by username
    result = await db.execute(
        select(User).where(User.username == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username}
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout (client should discard token)"""
    
    # In a more complex system, you might want to blacklist the token
    # For now, just return success
    return {"message": "Successfully logged out"}


class SignalWireToken(BaseModel):
    token: str
    project_id: str
    space_url: str
    from_number: str


@router.post("/signalwire-token", response_model=SignalWireToken)
async def get_signalwire_token(current_user: User = Depends(get_current_user)):
    """Get SignalWire token for WebRTC client"""
    
    if not all([settings.signalwire_project_id, settings.signalwire_token, settings.signalwire_space_url]):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SignalWire credentials not configured"
        )
    
    try:
        # Create auth header
        auth_string = f"{settings.signalwire_project_id}:{settings.signalwire_token}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json"
        }
        
        # Request subscriber token from SignalWire Call Fabric API
        logger.info(f"Requesting SignalWire token for reference: {current_user.username}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://{settings.signalwire_space_url}/api/fabric/subscribers/tokens",
                headers=headers,
                json={
                    "reference": current_user.username
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to get SignalWire token"
                )
            
            token_data = response.json()
            logger.info(f"SignalWire response: {token_data}")
            
            # SignalWire Call Fabric API returns 'token' field
            token_value = token_data.get("token")
            
            if not token_value:
                logger.error(f"No token in SignalWire response: {token_data}")
                raise ValueError("No token in response")
            
            return SignalWireToken(
                token=token_value,
                project_id=settings.signalwire_project_id,
                space_url=settings.signalwire_space_url,
                from_number=settings.signalwire_from_number or ""
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to get SignalWire token: {str(e)}"
        )