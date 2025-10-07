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
    Runs based on EXTRACTION_INTERVAL_MINUTES configuration.
    """
    try:
        logger.info("Starting scheduled extraction...")
        result = await extract_all_sources(database.db)
        logger.info(f"Scheduled extraction complete: {result}")

    except Exception as e:
        logger.error(f"Error in scheduled extraction: {e}")


async def scheduled_submission():
    """
    Submit pending content to AletheiaFact.
    Runs based on SUBMISSION_INTERVAL_MINUTES configuration (only if AUTO_SUBMIT_ENABLED=true).
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
        name='Extract from all sources',
        replace_existing=True
    )

    # Add submission job - runs every Y minutes (only if auto-submit is enabled)
    if settings.auto_submit_enabled:
        scheduler.add_job(
            scheduled_submission,
            trigger=IntervalTrigger(minutes=settings.submission_interval_minutes),
            id='submit_pending_content',
            name='Submit pending content to AletheiaFact',
            replace_existing=True
        )
        logger.info(
            f"Scheduler configured: extraction every {settings.extraction_interval_minutes} minutes, "
            f"submission every {settings.submission_interval_minutes} minutes (auto-submit enabled)"
        )
    else:
        logger.info(
            f"Scheduler configured: extraction every {settings.extraction_interval_minutes} minutes, "
            f"auto-submit disabled (use manual submission via dashboard)"
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
