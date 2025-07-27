from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import json
from core.database import get_db
from core.security import get_current_user, get_current_admin_user
from models import User, DocumentEmbedding
from services.vector_search import VectorSearchService
from pydantic import BaseModel

router = APIRouter(prefix="/api/documents", tags=["documents"])


class DocumentRequest(BaseModel):
    document_id: str
    title: str
    content: str
    category: Optional[str] = None
    meta_data: Optional[dict] = None


class DocumentResponse(BaseModel):
    document_id: str
    title: str
    content: str
    category: Optional[str]
    meta_data: dict


class SearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    limit: int = 5


class SearchResult(BaseModel):
    document_id: str
    title: str
    content: str
    similarity: float
    category: Optional[str]
    meta_data: dict


@router.post("/", response_model=dict)
async def create_document(
    document: DocumentRequest,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Create or update a document (admin only)"""
    
    vector_service = VectorSearchService()
    
    success = await vector_service.add_document(
        db,
        document_id=document.document_id,
        title=document.title,
        content=document.content,
        metadata=document.meta_data or {},
        category=document.category
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add document")
        
    return {"status": "success", "document_id": document.document_id}


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    category: Optional[str] = Form(None),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a document file (admin only)"""
    
    # Read file content
    content = await file.read()
    
    try:
        # For now, assume text files
        text_content = content.decode('utf-8')
    except:
        raise HTTPException(status_code=400, detail="Invalid file format")
        
    # Generate document ID from filename
    document_id = file.filename.replace(' ', '_').lower()
    
    vector_service = VectorSearchService()
    
    success = await vector_service.add_document(
        db,
        document_id=document_id,
        title=title,
        content=text_content,
        meta_data={
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(content)
        },
        category=category
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to upload document")
        
    return {"status": "success", "document_id": document_id}


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all documents"""
    
    from sqlalchemy import select
    
    query = select(DocumentEmbedding)
    if category:
        query = query.where(DocumentEmbedding.category == category)
        
    result = await db.execute(query)
    documents = result.scalars().all()
    
    return [
        DocumentResponse(
            document_id=doc.document_id,
            title=doc.title,
            content=doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
            category=doc.category,
            meta_data=doc.meta_data or {}
        )
        for doc in documents
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get document details"""
    
    from sqlalchemy import select
    
    result = await db.execute(
        select(DocumentEmbedding).where(DocumentEmbedding.document_id == document_id)
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    return DocumentResponse(
        document_id=doc.document_id,
        title=doc.title,
        content=doc.content,
        category=doc.category,
        meta_data=doc.meta_data or {}
    )


@router.post("/search", response_model=List[SearchResult])
async def search_documents(
    search: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search documents using vector similarity"""
    
    vector_service = VectorSearchService()
    
    results = await vector_service.search_documents(
        query=search.query,
        db=db,
        limit=search.limit,
        category=search.category
    )
    
    return [
        SearchResult(
            document_id=r["document_id"],
            title=r["title"],
            content=r["content"][:200] + "..." if len(r["content"]) > 200 else r["content"],
            similarity=r["similarity"],
            category=r["category"],
            meta_data=r["meta_data"] or {}
        )
        for r in results
    ]


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a document (admin only)"""
    
    vector_service = VectorSearchService()
    
    success = await vector_service.delete_document(db, document_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
        
    return {"status": "success", "message": "Document deleted"}


@router.post("/reindex")
async def reindex_documents(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Trigger reindexing of all documents (admin only)"""
    
    # This would typically trigger a background job
    # For now, just return success
    return {"status": "success", "message": "Reindexing started"}