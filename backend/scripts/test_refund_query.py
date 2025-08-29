#!/usr/bin/env python3
"""Test vector search for refund-related query"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from core.database import get_db
from services.vector_search import VectorSearchService
from services.openai_service import OpenAIService

async def test_refund_query():
    """Test what documents would be returned for a refund query"""
    
    # Get database session
    async for db in get_db():
        # Initialize services
        vector_service = VectorSearchService()
        openai_service = OpenAIService()
        
        # The customer's statement
        customer_text = "Yes. I would like a refund."
        
        print(f"\nCustomer said: '{customer_text}'")
        print("-" * 80)
        
        # Generate search query from customer text
        # In real usage, this would include conversation context
        search_query = await openai_service.generate_search_query(
            customer_text,
            ["refund", "return", "money back"]
        )
        
        print(f"\nGenerated search query: '{search_query}'")
        print("-" * 80)
        
        # Search for relevant documents
        documents = await vector_service.search_documents(
            search_query,
            db,
            limit=5,
            similarity_threshold=0.5
        )
        
        print(f"\nFound {len(documents)} relevant documents:")
        print("-" * 80)
        
        for i, doc in enumerate(documents, 1):
            print(f"\n{i}. {doc['title']}")
            print(f"   Similarity: {doc['similarity']:.3f}")
            print(f"   Category: {doc['category']}")
            print(f"   Content preview: {doc['content'][:200]}...")
            if doc['meta_data']:
                print(f"   Metadata: {doc['meta_data']}")
        
        if not documents:
            print("\nNo documents found matching the refund query.")
            print("This could mean:")
            print("1. No refund-related documents have been uploaded to the system")
            print("2. The similarity threshold is too high")
            print("3. The embeddings need to be regenerated")
            
            # Check if there are any documents at all
            from sqlalchemy import select
            from models import DocumentEmbedding
            
            result = await db.execute(select(DocumentEmbedding).limit(5))
            sample_docs = result.scalars().all()
            
            print(f"\nTotal documents in system: {len(sample_docs)}")
            if sample_docs:
                print("\nSample documents available:")
                for doc in sample_docs:
                    print(f"- {doc.title} (Category: {doc.category})")
        break  # Exit the async for loop

if __name__ == "__main__":
    asyncio.run(test_refund_query())