"""Content management API endpoints"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.models.extracted_content import ContentStatus
from app.services.submission_service import SubmissionService
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/content", tags=["content"])


@router.get("")
async def list_content(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    source_name: Optional[str] = None,
    min_score: Optional[int] = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """List extracted content with filtering and pagination"""
    try:
        query = {}

        if status:
            query['status'] = status

        if source_name:
            query['sourceName'] = source_name

        if min_score is not None:
            query['preFilterScore'] = {'$gte': min_score}

        # Sort by extraction date descending
        content_list = await db.extracted_content.find(query)\
            .sort('extractedAt', -1)\
            .skip(skip)\
            .limit(limit)\
            .to_list(None)

        # Convert ObjectId to string
        for content in content_list:
            content['_id'] = str(content['_id'])

        total = await db.extracted_content.count_documents(query)

        return {
            'content': content_list,
            'total': total,
            'skip': skip,
            'limit': limit
        }

    except Exception as e:
        logger.error(f"Error listing content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{content_id}")
async def get_content(
    content_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get a single content item by ID"""
    try:
        content = await db.extracted_content.find_one({'_id': ObjectId(content_id)})

        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        content['_id'] = str(content['_id'])
        return content

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{content_id}/submit")
async def submit_content(
    content_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Manually retry submission of a content item to AletheiaFact"""
    try:
        submission_service = SubmissionService(db)
        success = await submission_service.submit_content(content_id)

        if success:
            return {
                'message': 'Content submitted successfully',
                'contentId': content_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        else:
            # Get content to check error
            content = await db.extracted_content.find_one({'_id': ObjectId(content_id)})
            error = content.get('submissionError', 'Unknown error') if content else 'Content not found'

            raise HTTPException(
                status_code=400,
                detail=f"Submission failed: {error}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear-all")
async def clear_all_content(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Delete all extracted content (for testing purposes)"""
    try:
        result = await db.extracted_content.delete_many({})

        logger.info(f"Cleared all content: {result.deleted_count} items deleted")
        return {
            'message': 'All content cleared successfully',
            'deletedCount': result.deleted_count,
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error clearing content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{content_id}")
async def delete_content(
    content_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Delete a content item"""
    try:
        result = await db.extracted_content.delete_one({'_id': ObjectId(content_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Content not found")

        logger.info(f"Deleted content: {content_id}")
        return {'message': 'Content deleted successfully'}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting content: {e}")
        raise HTTPException(status_code=500, detail=str(e))
