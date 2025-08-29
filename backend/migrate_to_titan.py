#!/usr/bin/env python
"""
Migration script to switch from sentence-transformers to Bedrock Titan embeddings
This will:
1. Drop existing 768D embeddings
2. Recreate column with 1024D for Titan v2
3. Re-embed all documents using Bedrock Titan
"""

import asyncio
import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text
from core.config import settings
from services.embedding_service import get_embedding_service
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def drop_and_recreate_embeddings(db: AsyncSession):
    """Drop old embedding column and create new one with 1024 dimensions"""
    try:
        logger.info("🗑️ Dropping old embedding column...")
        await db.execute(text("ALTER TABLE document_embeddings DROP COLUMN IF EXISTS embedding"))
        await db.commit()
        
        logger.info("✨ Creating new embedding column with 1024 dimensions for Titan v2...")
        await db.execute(text("ALTER TABLE document_embeddings ADD COLUMN embedding vector(1024)"))
        await db.commit()
        
        logger.info("✅ Database schema updated successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Error updating database schema: {e}")
        await db.rollback()
        return False


async def reembed_all_documents(db: AsyncSession):
    """Re-embed all documents using Bedrock Titan"""
    embedding_service = get_embedding_service()
    
    try:
        # Get all documents from document_embeddings table
        result = await db.execute(text("""
            SELECT id, document_id, title, content 
            FROM document_embeddings 
            WHERE content IS NOT NULL AND content != ''
        """))
        documents = result.fetchall()
        
        if not documents:
            logger.warning("No documents found to embed")
            return True
            
        logger.info(f"📚 Found {len(documents)} documents to embed")
        
        for i, doc in enumerate(documents, 1):
            id, doc_id, title, content = doc
            
            try:
                # Generate embedding using Bedrock Titan
                logger.info(f"🔄 Processing document {i}/{len(documents)}: {title}")
                
                # Combine title and content for embedding
                text_to_embed = f"{title}\n\n{content}" if title else content
                
                # Generate embedding
                embedding = embedding_service.generate_embedding(text_to_embed)
                
                if not embedding:
                    logger.warning(f"⚠️ Empty embedding for document {doc_id}")
                    continue
                
                # Update the existing record with new embedding
                # Format embedding as PostgreSQL array string
                embedding_str = f"[{','.join(map(str, embedding))}]"
                
                await db.execute(text("""
                    UPDATE document_embeddings 
                    SET embedding = CAST(:embedding AS vector),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                """), {
                    "id": id,
                    "embedding": embedding_str
                })
                
                await db.commit()
                logger.info(f"✅ Embedded document {i}/{len(documents)}: {title} (dimension: {len(embedding)})")
                
            except Exception as e:
                logger.error(f"❌ Error embedding document {doc_id}: {e}")
                await db.rollback()
                continue
                
        logger.info(f"🎉 Successfully re-embedded all documents with Bedrock Titan")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during re-embedding: {e}")
        await db.rollback()
        return False


async def verify_embeddings(db: AsyncSession):
    """Verify the new embeddings are working"""
    try:
        # Check embedding dimensions
        result = await db.execute(text("""
            SELECT 
                COUNT(*) as count,
                AVG(array_length(embedding::text::text[], 1)) as avg_dimension
            FROM document_embeddings
            WHERE embedding IS NOT NULL
        """))
        
        stats = result.fetchone()
        if stats and stats.count > 0:
            logger.info(f"📊 Verification: {stats.count} embeddings with average dimension {stats.avg_dimension}")
            
            # Test a search query
            embedding_service = get_embedding_service()
            test_query = "refund policy"
            query_embedding = embedding_service.generate_embedding(test_query)
            
            # Search for similar documents
            # Format embedding as PostgreSQL array string
            query_embedding_str = f"[{','.join(map(str, query_embedding))}]"
            
            result = await db.execute(text("""
                SELECT title, 
                       1 - (embedding <=> CAST(:query_embedding AS vector)) as similarity
                FROM document_embeddings
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:query_embedding AS vector)
                LIMIT 3
            """), {"query_embedding": query_embedding_str})
            
            matches = result.fetchall()
            logger.info(f"🔍 Test search for '{test_query}':")
            for title, similarity in matches:
                logger.info(f"  - {title}: {similarity:.2%} similarity")
                
            return True
        else:
            logger.warning("⚠️ No embeddings found to verify")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error verifying embeddings: {e}")
        return False


async def main():
    """Main migration function"""
    logger.info("🚀 Starting migration to Bedrock Titan embeddings...")
    
    # Create database connection
    # Convert to async URL format
    database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(database_url, echo=False)
    
    async with AsyncSession(engine) as db:
        # Step 1: Drop and recreate embedding column
        if not await drop_and_recreate_embeddings(db):
            logger.error("Failed to update database schema")
            return
            
        # Step 2: Re-embed all documents
        if not await reembed_all_documents(db):
            logger.error("Failed to re-embed documents")
            return
            
        # Step 3: Verify embeddings
        if not await verify_embeddings(db):
            logger.warning("Verification failed, but embeddings may still be working")
            
    await engine.dispose()
    logger.info("✨ Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())