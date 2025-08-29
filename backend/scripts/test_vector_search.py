#!/usr/bin/env python3
"""Test vector search functionality"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

async def main():
    from core.database import AsyncSessionLocal
    from services.vector_search import VectorSearchService
    from services.openai_service import OpenAIService
    from sqlalchemy import select
    from models import DocumentEmbedding
    
    async with AsyncSessionLocal() as db:
        try:
            # Check what documents are in the database
            result = await db.execute(select(DocumentEmbedding))
            docs = result.scalars().all()
            
            print(f"\nDocuments in database: {len(docs)}")
            print("-" * 80)
            
            for doc in docs:
                print(f"\nID: {doc.document_id}")
                print(f"Title: {doc.title}")
                print(f"Category: {doc.category}")
                print(f"Content preview: {doc.content[:100]}...")
                print(f"Has embedding: {'Yes' if doc.embedding is not None else 'No'}")
            
            if docs:
                # Test search
                vector_service = VectorSearchService()
                
                # Test refund query
                customer_query = "Yes. I would like a refund."
                print(f"\n\nTesting search for: '{customer_query}'")
                print("-" * 80)
                
                results = await vector_service.search_documents(
                    customer_query,
                    db,
                    limit=3,
                    similarity_threshold=0.3  # Lower threshold
                )
                
                print(f"\nFound {len(results)} results:")
                for i, result in enumerate(results, 1):
                    print(f"\n{i}. {result['title']}")
                    print(f"   Similarity: {result['similarity']:.3f}")
                    print(f"   Content: {result['content'][:200]}...")
            else:
                print("\nNo documents found. Run 'make init' or 'docker-compose exec backend python init_demo.py' to add sample data.")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())