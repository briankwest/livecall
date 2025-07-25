"""
Add sentiment fields to calls table and create sentiment_history table
"""
import asyncio
import asyncpg
import os

async def run_migration():
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@livecall-postgres:5432/livecall')
    
    # Connect to database
    conn = await asyncpg.connect(database_url)
    
    try:
        # Add sentiment fields to calls table
        await conn.execute("""
            ALTER TABLE calls 
            ADD COLUMN IF NOT EXISTS current_sentiment VARCHAR(20) DEFAULT 'neutral',
            ADD COLUMN IF NOT EXISTS sentiment_confidence FLOAT DEFAULT 0.0,
            ADD COLUMN IF NOT EXISTS sentiment_updated_at TIMESTAMP WITH TIME ZONE;
        """)
        print("Added sentiment fields to calls table")
        
        # Create sentiment_history table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sentiment_history (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                call_id UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
                sentiment VARCHAR(20) NOT NULL,
                confidence FLOAT NOT NULL,
                transcription_context TEXT,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create index on call_id
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentiment_history_call_id 
            ON sentiment_history(call_id);
        """)
        
        print("Created sentiment_history table")
        
    except Exception as e:
        print(f"Error in migration: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())