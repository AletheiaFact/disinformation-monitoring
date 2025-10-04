"""Source management API endpoints"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.models.source import SourceConfiguration, CredibilityLevel
from app.extractors.rss_extractor import RSSExtractor, extract_all_sources
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sources", tags=["sources"])


class SourceCreate(SourceConfiguration):
    """Schema for creating a new source"""
    pass


class SourceUpdate(SourceConfiguration):
    """Schema for updating a source"""
    name: Optional[str] = None
    rssUrl: Optional[str] = None
    isActive: Optional[bool] = None
    credibilityLevel: Optional[CredibilityLevel] = None


@router.get("")
async def list_sources(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """List all RSS sources with pagination"""
    try:
        query = {}
        if active_only:
            query['isActive'] = True

        sources = await db.source_configuration.find(query).skip(skip).limit(limit).to_list(None)

        # Convert ObjectId to string
        for source in sources:
            source['_id'] = str(source['_id'])

        total = await db.source_configuration.count_documents(query)

        return {
            'sources': sources,
            'total': total,
            'skip': skip,
            'limit': limit
        }

    except Exception as e:
        logger.error(f"Error listing sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_source(
    source: SourceCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create a new RSS source"""
    try:
        # Check if source with same URL already exists
        existing = await db.source_configuration.find_one({'rssUrl': source.rssUrl})
        if existing:
            raise HTTPException(status_code=400, detail="Source with this RSS URL already exists")

        source_dict = source.model_dump()
        source_dict['createdAt'] = datetime.utcnow()
        source_dict['updatedAt'] = datetime.utcnow()

        result = await db.source_configuration.insert_one(source_dict)

        source_dict['_id'] = str(result.inserted_id)

        logger.info(f"Created new source: {source.name}")
        return source_dict

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{source_id}")
async def get_source(
    source_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get a single source by ID"""
    try:
        source = await db.source_configuration.find_one({'_id': ObjectId(source_id)})

        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        source['_id'] = str(source['_id'])
        return source

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{source_id}")
async def update_source(
    source_id: str,
    updates: dict,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update a source configuration"""
    try:
        # Check if source exists
        existing = await db.source_configuration.find_one({'_id': ObjectId(source_id)})
        if not existing:
            raise HTTPException(status_code=404, detail="Source not found")

        # Prepare update data
        update_data = {k: v for k, v in updates.items() if v is not None}
        update_data['updatedAt'] = datetime.utcnow()

        # Update source
        result = await db.source_configuration.update_one(
            {'_id': ObjectId(source_id)},
            {'$set': update_data}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="No changes made")

        # Return updated source
        updated_source = await db.source_configuration.find_one({'_id': ObjectId(source_id)})
        updated_source['_id'] = str(updated_source['_id'])

        logger.info(f"Updated source: {source_id}")
        return updated_source

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{source_id}")
async def delete_source(
    source_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Delete a source"""
    try:
        result = await db.source_configuration.delete_one({'_id': ObjectId(source_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Source not found")

        logger.info(f"Deleted source: {source_id}")
        return {'message': 'Source deleted successfully'}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-all")
async def extract_from_all_sources(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Manually trigger extraction from all active sources"""
    try:
        logger.info("Manual extraction triggered for all sources")
        result = await extract_all_sources(db)

        return {
            'totalExtracted': result['totalExtracted'],
            'sourceCount': result['sourceCount'],
            'bySource': result['bySource'],
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error extracting from all sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{source_id}/extract")
async def extract_from_source(
    source_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Manually trigger extraction for a specific source"""
    try:
        # Get source
        source = await db.source_configuration.find_one({'_id': ObjectId(source_id)})
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Extract content using appropriate extractor
        from app.extractors.extractor_factory import ExtractorFactory
        count = await ExtractorFactory.extract_from_source(source, db)

        logger.info(f"Manual extraction from {source['name']}: {count} articles")
        return {
            'sourceName': source['name'],
            'extractedCount': count,
            'timestamp': datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting from source: {e}")
        raise HTTPException(status_code=500, detail=str(e))
