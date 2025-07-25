"""Add sentiment columns to transcriptions table"""
import asyncio
import sys
sys.path.append('/app')
from sqlalchemy import text
from core.database import engine
import logging

logger = logging.getLogger(__name__)


async def upgrade():
    """Add sentiment and sentiment_score columns to transcriptions table"""
    async with engine.begin() as conn:
        try:
            logger.info("Adding sentiment columns to transcriptions table...")
            
            # Add sentiment column (positive, neutral, negative)
            await conn.execute(text("""
                ALTER TABLE transcriptions 
                ADD COLUMN IF NOT EXISTS sentiment VARCHAR(20) DEFAULT 'neutral';
            """))
            
            # Add sentiment_score column (0.0 to 1.0)
            await conn.execute(text("""
                ALTER TABLE transcriptions 
                ADD COLUMN IF NOT EXISTS sentiment_score FLOAT DEFAULT 0.5;
            """))
            
            logger.info("Successfully added sentiment columns to transcriptions table")
        except Exception as e:
            logger.error(f"Error in migration: {e}")
            raise


async def downgrade():
    """Remove sentiment columns from transcriptions table"""
    async with engine.begin() as conn:
        try:
            logger.info("Removing sentiment columns from transcriptions table...")
            
            await conn.execute(text("""
                ALTER TABLE transcriptions 
                DROP COLUMN IF EXISTS sentiment;
            """))
            
            await conn.execute(text("""
                ALTER TABLE transcriptions 
                DROP COLUMN IF EXISTS sentiment_score;
            """))
            
            logger.info("Successfully removed sentiment columns from transcriptions table")
        except Exception as e:
            logger.error(f"Error in downgrade: {e}")
            raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(upgrade())