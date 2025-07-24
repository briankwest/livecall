-- Database schema for live call assistant

-- Calls table
CREATE TABLE calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signalwire_call_id VARCHAR(255) UNIQUE NOT NULL,
    phone_number VARCHAR(50),
    agent_id VARCHAR(255),
    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    status VARCHAR(50) DEFAULT 'active',
    listening_mode VARCHAR(20) DEFAULT 'both', -- 'agent', 'customer', 'both'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Call transcriptions
CREATE TABLE transcriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID REFERENCES calls(id) ON DELETE CASCADE,
    speaker VARCHAR(50), -- 'agent' or 'customer'
    text TEXT NOT NULL,
    confidence FLOAT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sequence_number INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- AI interactions
CREATE TABLE ai_interactions (
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
CREATE TABLE call_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID REFERENCES calls(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    key_topics TEXT[],
    sentiment_score FLOAT,
    action_items JSONB,
    meta_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Document references used during calls
CREATE TABLE call_document_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID REFERENCES calls(id) ON DELETE CASCADE,
    document_id VARCHAR(255),
    document_title TEXT,
    relevance_score FLOAT,
    accessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    context TEXT
);

-- Indexes for performance
CREATE INDEX idx_calls_signalwire_id ON calls(signalwire_call_id);
CREATE INDEX idx_calls_status ON calls(status);
CREATE INDEX idx_transcriptions_call_id ON transcriptions(call_id);
CREATE INDEX idx_transcriptions_timestamp ON transcriptions(timestamp);
CREATE INDEX idx_ai_interactions_call_id ON ai_interactions(call_id);
CREATE INDEX idx_summaries_call_id ON call_summaries(call_id);

-- Document embeddings table for pgvector
CREATE TABLE document_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id VARCHAR(255) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536), -- OpenAI ada-002 dimension
    meta_data JSONB DEFAULT '{}',
    category VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient vector search
CREATE INDEX idx_document_embeddings_embedding 
    ON document_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);