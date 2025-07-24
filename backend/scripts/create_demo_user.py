import asyncio
import asyncpg
from passlib.context import CryptContext
import uuid
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/livecall")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_demo_user():
    # Connect to database
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Create a demo user
        user_id = str(uuid.uuid4())
        email = "demo@example.com"
        password = "demo123"  # In production, use secure passwords
        hashed_password = pwd_context.hash(password)
        
        # Check if user already exists
        existing = await conn.fetchval(
            "SELECT id FROM users WHERE email = $1",
            email
        )
        
        if existing:
            print(f"User {email} already exists")
            return
        
        # Insert the user
        await conn.execute(
            """
            INSERT INTO users (id, email, username, hashed_password, full_name, is_active, is_admin)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            uuid.UUID(user_id),
            email,
            "demo",  # username
            hashed_password,
            "Demo User",  # full_name
            True,  # is_active
            False  # is_admin
        )
        
        print(f"Demo user created successfully!")
        print(f"Email: {email}")
        print(f"Password: {password}")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(create_demo_user())