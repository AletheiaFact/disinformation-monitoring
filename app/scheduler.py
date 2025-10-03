"""APScheduler configuration for periodic tasks"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import logging

from app.config import settings
from app.database import database
from app.extractors.rss_extractor import extract_all_sources
from app.services.submission_service import SubmissionService

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def scheduled_extraction():
    """
    Periodic task to extract content from all active sources.
    Runs every 30 minutes (configurable).
    """
    try:
        logger.info("Starting scheduled extraction...")
        result = await extract_all_sources(database.db)
        logger.info(f"Scheduled extraction complete: {result}")

        # Automatically submit pending content if auto-submit is enabled
        if settings.auto_submit_enabled and result['totalExtracted'] > 0:
            logger.info("Auto-submit enabled, proceeding with submission...")
            await scheduled_submission()
        elif result['totalExtracted'] > 0:
            logger.info(f"Auto-submit disabled, {result['totalExtracted']} items extracted but not submitted")

    except Exception as e:
        logger.error(f"Error in scheduled extraction: {e}")


async def scheduled_submission():
    """
    Submit pending content to AletheiaFact.
    Called after each extraction run.
    """
    try:
        logger.info("Starting scheduled submission...")
        submission_service = SubmissionService(database.db)
        result = await submission_service.submit_pending_content()
        logger.info(f"Scheduled submission complete: {result}")

    except Exception as e:
        logger.error(f"Error in scheduled submission: {e}")


def setup_scheduler():
    """Configure and start the scheduler"""

    # Add extraction job - runs every X minutes
    scheduler.add_job(
        scheduled_extraction,
        trigger=IntervalTrigger(minutes=settings.extraction_interval_minutes),
        id='extract_all_sources',
        name='Extract from all RSS sources',
        replace_existing=True,
        next_run_time=datetime.now()  # Run immediately on startup
    )

    logger.info(
        f"Scheduler configured: extraction every {settings.extraction_interval_minutes} minutes, "
        f"auto-submit: {'enabled' if settings.auto_submit_enabled else 'disabled'}"
    )


def start_scheduler():
    """Start the scheduler"""
    try:
        scheduler.start()
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        raise


def shutdown_scheduler():
    """Shutdown the scheduler gracefully"""
    try:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler shutdown complete")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {e}")
