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
    Periodic task to extract content from all active sources, then optionally submit pending items.
    Runs based on EXTRACTION_INTERVAL_MINUTES configuration.

    Flow:
    1. Extract content from all sources
    2. If AUTO_SUBMIT_ENABLED=true: Automatically submit pending verification requests to AletheiaFact

    Protected by APScheduler's max_instances=1 to prevent concurrent execution.
    """
    try:
        logger.info("Starting scheduled extraction...")
        extraction_result = await extract_all_sources(database.db)
        logger.info(f"Scheduled extraction complete: {extraction_result}")

        if settings.auto_submit_enabled:
            logger.info("Starting automatic submission of pending content (AUTO_SUBMIT_ENABLED=true)...")
            submission_service = SubmissionService(database.db)
            submission_result = await submission_service.submit_pending_content()
            logger.info(f"Automatic submission complete: {submission_result}")
        else:
            logger.info("Automatic submission skipped (AUTO_SUBMIT_ENABLED=false). Use manual submission via API or dashboard.")

    except Exception as e:
        logger.error(f"Error in scheduled extraction/submission: {e}")


def setup_scheduler():
    """
    Configure and start the scheduler with race condition protection.

    Single unified job that:
    1. Extracts content from all sources
    2. Automatically submits pending verification requests

    This ensures submissions happen immediately after extraction without needing separate timers.
    """

    scheduler.add_job(
        scheduled_extraction,
        trigger=IntervalTrigger(minutes=settings.extraction_interval_minutes),
        id='extract_and_submit',
        name='Extract content and submit pending VRs',
        max_instances=1,
        coalesce=True,
        replace_existing=True
    )

    if settings.auto_submit_enabled:
        logger.info(
            f"Scheduler configured: extraction + automatic submission every {settings.extraction_interval_minutes} minutes"
        )
    else:
        logger.info(
            f"Scheduler configured: extraction every {settings.extraction_interval_minutes} minutes "
            f"(auto-submit disabled - use manual submission via API)"
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
