# Vector Database Integration Design

## Overview
Use pgvector extension in PostgreSQL to provide real-time contextual documentation to agents during calls.

## Architecture

### 1. Document Ingestion Pipeline
```python
# Document processing flow
1. Load documentation (PDF, MD, TXT, HTML)
2. Chunk documents (500-1000 tokens per chunk)
3. Generate embeddings using OpenAI text-embedding-ada-002
4. Store in PostgreSQL with pgvector
```

### 2. Vector Database Schema (pgvector)
```sql
-- document_embeddings table
{
  "id": "uuid",
  "document_id": "doc_123",
  "title": "Product Manual",
  "content": "Original chunk text...",
  "embedding": "vector(1536)",  -- pgvector type
  "metadata": {
    "source": "product_manual.pdf",
    "page": 42,
    "section": "Troubleshooting",
    "category": "technical",
    "last_updated": "2024-01-01"
  }
}
```

### 3. Real-time Search Strategy
```python
# Conversation context window
- Keep last 5-10 conversation turns
- Extract key topics/entities using OpenAI
- Generate search query embedding
- Retrieve top-k relevant documents using pgvector
- Re-rank based on conversation flow
```

### 4. pgvector Search Query
```sql
-- Find similar documents using cosine similarity
SELECT 
    document_id,
    title,
    content,
    1 - (embedding <=> %s) as similarity,
    metadata
FROM document_embeddings
WHERE 1 - (embedding <=> %s) > 0.7  -- similarity threshold
ORDER BY embedding <=> %s
LIMIT 5;
```

### 5. Relevance Scoring
- **Semantic similarity**: Cosine distance via pgvector
- **Recency weight**: Boost recently accessed docs
- **Context coherence**: Prefer docs from same category
- **Agent feedback**: Learn from doc usage patterns

### 6. Performance Optimization
- Use IVFFlat index for faster searches
- Batch embedding operations
- Cache frequently accessed results in Redis
- Pre-filter by category when applicable