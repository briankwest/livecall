"""
Add direction column to calls table
"""
import asyncio
import sys
sys.path.append('/app')
from sqlalchemy import text
from core.database import engine
import logging

logger = logging.getLogger(__name__)

async def upgrade():
    """Add direction column to calls table"""
    async with engine.begin() as conn:
        try:
            # Check if column already exists
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='calls' AND column_name='direction'
            """))
            
            if not result.fetchone():
                # Add direction column to calls table
                await conn.execute(text("""
                    ALTER TABLE calls 
                    ADD COLUMN direction VARCHAR(20) DEFAULT 'outbound' NOT NULL;
                """))
                logger.info("Added direction column to calls table")
            else:
                logger.info("Direction column already exists in calls table")
                
        except Exception as e:
            logger.error(f"Error in migration: {e}")
            raise

async def downgrade():
    """Remove direction column"""
    async with engine.begin() as conn:
        try:
            # Remove direction column from calls table
            await conn.execute(text("""
                ALTER TABLE calls 
                DROP COLUMN IF EXISTS direction;
            """))
            
            logger.info("Removed direction column from calls table")
            
        except Exception as e:
            logger.error(f"Error in downgrade: {e}")
            raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(upgrade())