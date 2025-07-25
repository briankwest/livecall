"""
Run all database migrations
"""
import asyncio
import sys
import os
sys.path.append('/app')
from sqlalchemy import text
from core.database import engine
import logging

logger = logging.getLogger(__name__)

async def run_all_migrations():
    """Run all database migrations in order"""
    
    # Import and run each migration
    migration_modules = [
        'migrations.add_direction_column',
        'migrations.add_raw_data_column', 
        'migrations.add_sentiment_fields',
        'migrations.add_sentiment_columns'
    ]
    
    for module_name in migration_modules:
        try:
            logger.info(f"Running migration: {module_name}")
            module = __import__(module_name, fromlist=['upgrade'])
            if hasattr(module, 'upgrade'):
                await module.upgrade()
                logger.info(f"Completed migration: {module_name}")
        except Exception as e:
            logger.error(f"Failed to run migration {module_name}: {e}")
            # Continue with other migrations even if one fails
            continue

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_all_migrations())