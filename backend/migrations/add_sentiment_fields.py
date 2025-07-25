"""
Add sentiment fields to calls table and create sentiment_history table
"""
import asyncio
import sys
sys.path.append('/app')
from sqlalchemy import text
from core.database import engine
import logging

logger = logging.getLogger(__name__)

async def upgrade():
    """Add sentiment fields to calls table and create sentiment_history table"""
    async with engine.begin() as conn:
        try:
            # Add sentiment fields to calls table
            await conn.execute(text("""
                ALTER TABLE calls 
                ADD COLUMN IF NOT EXISTS current_sentiment VARCHAR(20) DEFAULT 'neutral',
                ADD COLUMN IF NOT EXISTS sentiment_confidence FLOAT DEFAULT 0.0,
                ADD COLUMN IF NOT EXISTS sentiment_updated_at TIMESTAMP WITH TIME ZONE;
            """))
            logger.info("Added sentiment fields to calls table")
            
            # Create sentiment_history table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sentiment_history (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    call_id UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
                    sentiment VARCHAR(20) NOT NULL,
                    confidence FLOAT NOT NULL,
                    transcription_context TEXT,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_sentiment_history_call FOREIGN KEY (call_id) REFERENCES calls(id)
                );
            """))
            
            # Create index on call_id for better query performance
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_sentiment_history_call_id 
                ON sentiment_history(call_id);
            """))
            
            logger.info("Created sentiment_history table")
            
        except Exception as e:
            logger.error(f"Error in migration: {e}")
            raise

async def downgrade():
    """Remove sentiment fields and table"""
    async with engine.begin() as conn:
        try:
            # Drop sentiment_history table
            await conn.execute(text("DROP TABLE IF EXISTS sentiment_history CASCADE;"))
            
            # Remove sentiment fields from calls table
            await conn.execute(text("""
                ALTER TABLE calls 
                DROP COLUMN IF EXISTS current_sentiment,
                DROP COLUMN IF EXISTS sentiment_confidence,
                DROP COLUMN IF EXISTS sentiment_updated_at;
            """))
            
            logger.info("Removed sentiment fields and table")
            
        except Exception as e:
            logger.error(f"Error in downgrade: {e}")
            raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(upgrade())