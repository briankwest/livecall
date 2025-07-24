from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pgvector.sqlalchemy import Vector
import numpy as np
import logging
from models import DocumentEmbedding
from .openai_service import OpenAIService

logger = logging.getLogger(__name__)


class VectorSearchService:
    def __init__(self):
        self.openai_service = OpenAIService()
        
    async def search_documents(
        self,
        query: str,
        db: AsyncSession,
        limit: int = 5,
        similarity_threshold: float = 0.7,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search documents using vector similarity"""
        
        if not query:
            return []
            
        try:
            # Generate embedding for query
            query_embedding = await self.openai_service.generate_embedding(query)
            
            # Build the search query with pgvector
            sql = text("""
                SELECT 
                    document_id,
                    title,
                    content,
                    1 - (embedding <=> :embedding) as similarity,
                    meta_data,
                    category
                FROM document_embeddings
                WHERE 1 - (embedding <=> :embedding) > :threshold
                    AND (:category IS NULL OR category = :category)
                ORDER BY embedding <=> :embedding
                LIMIT :limit
            """)
            
            result = await db.execute(
                sql,
                {
                    "embedding": query_embedding,
                    "threshold": similarity_threshold,
                    "category": category,
                    "limit": limit
                }
            )
            
            documents = []
            for row in result:
                documents.append({
                    "document_id": row.document_id,
                    "title": row.title,
                    "content": row.content,
                    "similarity": float(row.similarity),
                    "metadata": row.meta_data,
                    "category": row.category
                })
                
            return documents
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
            
    async def add_document(
        self,
        db: AsyncSession,
        document_id: str,
        title: str,
        content: str,
        meta_data: Dict[str, Any] = None,
        category: Optional[str] = None
    ) -> bool:
        """Add document with embedding to database"""
        
        try:
            # Generate embedding
            embedding = await self.openai_service.generate_embedding(content)
            
            # Check if document already exists
            existing = await db.execute(
                select(DocumentEmbedding).where(DocumentEmbedding.document_id == document_id)
            )
            doc = existing.scalar_one_or_none()
            
            if doc:
                # Update existing document
                doc.title = title
                doc.content = content
                doc.embedding = embedding
                doc.meta_data = meta_data or {}
                doc.category = category
            else:
                # Create new document
                doc = DocumentEmbedding(
                    document_id=document_id,
                    title=title,
                    content=content,
                    embedding=embedding,
                    meta_data=meta_data or {},
                    category=category
                )
                db.add(doc)
                
            await db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            await db.rollback()
            return False
            
    async def delete_document(
        self,
        db: AsyncSession,
        document_id: str
    ) -> bool:
        """Delete document from database"""
        
        try:
            result = await db.execute(
                select(DocumentEmbedding).where(DocumentEmbedding.document_id == document_id)
            )
            doc = result.scalar_one_or_none()
            
            if doc:
                await db.delete(doc)
                await db.commit()
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            await db.rollback()
            return False
            
    async def search_similar_documents(
        self,
        db: AsyncSession,
        document_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find documents similar to a given document"""
        
        try:
            # Get the document's embedding
            result = await db.execute(
                select(DocumentEmbedding).where(DocumentEmbedding.document_id == document_id)
            )
            doc = result.scalar_one_or_none()
            
            if not doc or not doc.embedding:
                return []
                
            # Search for similar documents
            sql = text("""
                SELECT 
                    document_id,
                    title,
                    content,
                    1 - (embedding <=> :embedding) as similarity,
                    meta_data,
                    category
                FROM document_embeddings
                WHERE document_id != :exclude_id
                ORDER BY embedding <=> :embedding
                LIMIT :limit
            """)
            
            result = await db.execute(
                sql,
                {
                    "embedding": doc.embedding,
                    "exclude_id": document_id,
                    "limit": limit
                }
            )
            
            documents = []
            for row in result:
                documents.append({
                    "document_id": row.document_id,
                    "title": row.title,
                    "content": row.content,
                    "similarity": float(row.similarity),
                    "metadata": row.meta_data,
                    "category": row.category
                })
                
            return documents
            
        except Exception as e:
            logger.error(f"Error finding similar documents: {e}")
            return []