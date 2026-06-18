import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from database import async_session_maker
from chat.models import WebsiteSource
from docs.crawler import crawl_website

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def nightly_sync_job():
    """
    Finds all active website sources and re-crawls them.
    Runs every night.
    """
    logger.info("Starting nightly website sync job...")
    try:
        async with async_session_maker() as session:
            # Find all sources that were previously successfully crawled or pending
            result = await session.execute(
                select(WebsiteSource).filter(WebsiteSource.status.in_(["completed", "pending"]))
            )
            sources = result.scalars().all()

            for source in sources:
                logger.info(f"Auto-syncing source {source.base_url}")
                try:
                    await crawl_website(str(source.id), session)
                except Exception as e:
                    logger.error(f"Failed to auto-sync {source.base_url}: {e}")
                    
    except Exception as e:
        logger.error(f"Error in nightly sync job: {e}")

def start_scheduler():
    """Initializes and starts the background scheduler."""
    scheduler.add_job(nightly_sync_job, 'cron', hour=2, minute=0)
    scheduler.start()
    logger.info("Started background auto-sync scheduler.")
