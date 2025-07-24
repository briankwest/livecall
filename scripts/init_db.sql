-- Initialize database with schema from database_schema.sql

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Calls table
CREATE TABLE IF NOT EXISTS calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signalwire_call_id VARCHAR(255) UNIQUE NOT NULL,
    phone_number VARCHAR(50),
    agent_id VARCHAR(255),
    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    status VARCHAR(50) DEFAULT 'active',
    listening_mode VARCHAR(20) DEFAULT 'both',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Call transcriptions
CREATE TABLE IF NOT EXISTS transcriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID REFERENCES calls(id) ON DELETE CASCADE,
    speaker VARCHAR(50),
    text TEXT NOT NULL,
    confidence FLOAT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sequence_number INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- AI interactions
CREATE TABLE IF NOT EXISTS ai_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID REFERENCES calls(id) ON DELETE CASCADE,
    transcription_id UUID REFERENCES transcriptions(id),
    prompt TEXT NOT NULL,
    response TEXT,
    vector_search_results JSONB,
    relevance_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Call summaries
CREATE TABLE IF NOT EXISTS call_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID REFERENCES calls(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    key_topics TEXT[],
    sentiment_score FLOAT,
    action_items JSONB,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Document references used during calls
CREATE TABLE IF NOT EXISTS call_document_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID REFERENCES calls(id) ON DELETE CASCADE,
    document_id VARCHAR(255),
    document_title TEXT,
    relevance_score FLOAT,
    accessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    context TEXT
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_calls_signalwire_id ON calls(signalwire_call_id);
CREATE INDEX IF NOT EXISTS idx_calls_status ON calls(status);
CREATE INDEX IF NOT EXISTS idx_transcriptions_call_id ON transcriptions(call_id);
CREATE INDEX IF NOT EXISTS idx_transcriptions_timestamp ON transcriptions(timestamp);
CREATE INDEX IF NOT EXISTS idx_ai_interactions_call_id ON ai_interactions(call_id);
CREATE INDEX IF NOT EXISTS idx_summaries_call_id ON call_summaries(call_id);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_calls_updated_at BEFORE UPDATE ON calls
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Document embeddings table for pgvector
CREATE TABLE IF NOT EXISTS document_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id VARCHAR(255) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    meta_data JSONB DEFAULT '{}',
    category VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for vector similarity search
CREATE INDEX IF NOT EXISTS idx_document_embeddings_embedding 
    ON document_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Create index on document_id for lookups
CREATE INDEX IF NOT EXISTS idx_document_embeddings_document_id 
    ON document_embeddings(document_id);

-- Create index on category for filtering
CREATE INDEX IF NOT EXISTS idx_document_embeddings_category 
    ON document_embeddings(category);

-- Create updated_at trigger for embeddings
CREATE TRIGGER update_document_embeddings_updated_at BEFORE UPDATE ON document_embeddings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();