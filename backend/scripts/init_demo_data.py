import asyncio
import uuid
from datetime import datetime, timedelta
import asyncpg
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/livecall")


async def init_demo_data():
    # Connect to database
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Create pgvector extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        
        # Initialize some demo documents
        documents = [
            {
                "id": str(uuid.uuid4()),
                "document_id": "DOC001",
                "title": "Customer Support Best Practices",
                "content": "When handling customer calls, always greet the customer warmly and listen actively to their concerns. Empathy is key to building rapport.",
                "category": "support",
                "meta_data": {"tags": ["customer service", "communication", "best practices"]}
            },
            {
                "id": str(uuid.uuid4()),
                "document_id": "DOC002",
                "title": "Product Return Policy",
                "content": "Our return policy allows customers to return products within 30 days of purchase. Items must be in original condition with receipt.",
                "category": "policy",
                "meta_data": {"tags": ["returns", "policy", "refunds"]}
            },
            {
                "id": str(uuid.uuid4()),
                "document_id": "DOC003",
                "title": "Technical Troubleshooting Guide",
                "content": "For connectivity issues, first verify the customer's internet connection. Ask them to restart their device and check cable connections.",
                "category": "technical",
                "meta_data": {"tags": ["troubleshooting", "technical support", "connectivity"]}
            }
        ]
        
        # Insert documents (without embeddings for now)
        for doc in documents:
            query = """
            INSERT INTO document_embeddings (id, document_id, title, content, category, meta_data)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (document_id) DO NOTHING
            """
            await conn.execute(
                query,
                uuid.UUID(doc["id"]), 
                doc["document_id"], 
                doc["title"], 
                doc["content"], 
                doc["category"], 
                json.dumps(doc["meta_data"])
            )
        
        print("Demo data initialized successfully!")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(init_demo_data())