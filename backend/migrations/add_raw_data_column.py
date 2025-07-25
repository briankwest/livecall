"""
Add raw_data column to calls and transcriptions tables
"""
import asyncio
import sys
sys.path.append('/app')
from sqlalchemy import text
from core.database import engine
import logging

logger = logging.getLogger(__name__)

async def upgrade():
    """Add raw_data JSONB columns to calls and transcriptions tables"""
    async with engine.begin() as conn:
        try:
            # Check if raw_data column exists in calls table
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='calls' AND column_name='raw_data'
            """))
            
            if not result.fetchone():
                # Add raw_data column to calls table
                await conn.execute(text("""
                    ALTER TABLE calls 
                    ADD COLUMN raw_data JSONB DEFAULT '{}' NOT NULL;
                """))
                logger.info("Added raw_data column to calls table")
            else:
                logger.info("raw_data column already exists in calls table")
            
            # Check if raw_data column exists in transcriptions table
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='transcriptions' AND column_name='raw_data'
            """))
            
            if not result.fetchone():
                # Add raw_data column to transcriptions table
                await conn.execute(text("""
                    ALTER TABLE transcriptions 
                    ADD COLUMN raw_data JSONB DEFAULT '{}' NOT NULL;
                """))
                logger.info("Added raw_data column to transcriptions table")
            else:
                logger.info("raw_data column already exists in transcriptions table")
                
        except Exception as e:
            logger.error(f"Error in migration: {e}")
            raise

async def downgrade():
    """Remove raw_data columns"""
    async with engine.begin() as conn:
        try:
            # Remove raw_data columns
            await conn.execute(text("""
                ALTER TABLE calls 
                DROP COLUMN IF EXISTS raw_data;
            """))
            
            await conn.execute(text("""
                ALTER TABLE transcriptions 
                DROP COLUMN IF EXISTS raw_data;
            """))
            
            logger.info("Removed raw_data columns")
            
        except Exception as e:
            logger.error(f"Error in downgrade: {e}")
            raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(upgrade())