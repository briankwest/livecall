#!/usr/bin/env python3
"""Initialize database with demo data"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.database import engine, AsyncSessionLocal
from backend.core.security import get_password_hash
from backend.models import Base, User, DocumentEmbedding
from backend.services.vector_search import VectorSearchService

async def init_database():
    """Initialize database tables and demo data"""
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("Database tables created successfully")
    
    # Create demo user
    async with AsyncSessionLocal() as db:
        # Check if demo user exists
        from sqlalchemy import select
        result = await db.execute(
            select(User).where(User.username == "demo")
        )
        demo_user = result.scalar_one_or_none()
        
        if not demo_user:
            demo_user = User(
                email="demo@example.com",
                username="demo",
                hashed_password=get_password_hash("demo123"),
                full_name="Demo User",
                is_active=True,
                is_admin=True  # Admin for testing
            )
            db.add(demo_user)
            await db.commit()
            print("Demo user created: username=demo, password=demo123")
        else:
            print("Demo user already exists")
        
        # Add sample documents
        vector_service = VectorSearchService()
        
        sample_docs = [
            {
                "document_id": "refund_policy",
                "title": "Refund Policy Guidelines",
                "content": """Our refund policy ensures customer satisfaction:
                
1. Full refunds are available within 30 days of purchase
2. Items must be in original condition with tags attached
3. Digital products are non-refundable after download
4. Shipping costs are non-refundable
5. Refunds are processed within 5-7 business days

For special circumstances, contact customer service for assistance.""",
                "category": "policies"
            },
            {
                "document_id": "account_recovery",
                "title": "Account Recovery Process",
                "content": """To recover your account:

1. Click 'Forgot Password' on the login page
2. Enter your registered email address
3. Check your email for a reset link (valid for 24 hours)
4. Click the link and create a new password
5. Use at least 8 characters with mixed case and numbers

If you don't receive the email, check spam folder or contact support.""",
                "category": "technical"
            },
            {
                "document_id": "shipping_info",
                "title": "Shipping Information",
                "content": """Shipping options and timelines:

Standard Shipping (5-7 business days): $5.99
Express Shipping (2-3 business days): $12.99
Overnight Shipping (1 business day): $24.99

Free shipping on orders over $50
International shipping available to select countries
Tracking information provided via email
Signature may be required for high-value items""",
                "category": "shipping"
            }
        ]
        
        for doc in sample_docs:
            success = await vector_service.add_document(
                db,
                document_id=doc["document_id"],
                title=doc["title"],
                content=doc["content"],
                category=doc["category"]
            )
            if success:
                print(f"Added document: {doc['title']}")
            else:
                print(f"Failed to add document: {doc['title']}")

if __name__ == "__main__":
    asyncio.run(init_database())