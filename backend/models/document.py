from sqlalchemy import Column, String, Text, DateTime, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid
from core.database import Base


class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))
    meta_data = Column(JSON, default={})
    category = Column(String(100), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Create index for vector similarity search
    __table_args__ = (
        Index('idx_document_embeddings_embedding', 'embedding', postgresql_using='ivfflat',
              postgresql_ops={'embedding': 'vector_cosine_ops'}),
    )