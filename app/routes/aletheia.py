"""AletheiaFact API integration endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.database import get_database
from app.services.submission_service import SubmissionService
from app.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/aletheia", tags=["aletheia"])


class AutoSubmitConfig(BaseModel):
    enabled: bool


@router.get("/auto-submit/status")
async def get_auto_submit_status():
    """Get current auto-submit configuration status"""
    return {
        'enabled': settings.auto_submit_enabled,
        'description': 'Automatic submission of content to AletheiaFact after extraction'
    }


@router.post("/auto-submit/toggle")
async def toggle_auto_submit(config: AutoSubmitConfig):
    """Toggle automatic submission on/off at runtime"""
    settings.auto_submit_enabled = config.enabled
    logger.info(f"Auto-submit {'enabled' if config.enabled else 'disabled'} by API request")

    return {
        'message': f"Auto-submit {'enabled' if config.enabled else 'disabled'}",
        'enabled': settings.auto_submit_enabled
    }


@router.post("/submit-pending")
async def submit_pending(
    limit: int = Query(100, description="Maximum number of items to submit"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Manually trigger submission of all pending content"""
    try:
        submission_service = SubmissionService(db)
        result = await submission_service.submit_pending_content(limit=limit)

        return {
            'message': 'Batch submission complete',
            'result': result
        }

    except Exception as e:
        logger.error(f"Error submitting pending content: {e}")
        raise HTTPException(status_code=500, detail=str(e))
