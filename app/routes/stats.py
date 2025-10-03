"""Statistics API endpoints"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stats", tags=["statistics"])


@router.get("")
async def get_statistics(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get dashboard statistics"""
    try:
        # Calculate today's date range
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        # Extraction statistics
        total_today = await db.extracted_content.count_documents({
            'extractedAt': {'$gte': today_start, '$lt': today_end}
        })

        # Count by status
        status_counts = {}
        for status in ['pending', 'submitted', 'rejected', 'failed']:
            count = await db.extracted_content.count_documents({'status': status})
            status_counts[status] = count

        # Average score
        pipeline = [
            {'$group': {
                '_id': None,
                'avgScore': {'$avg': '$preFilterScore'}
            }}
        ]
        avg_result = await db.extracted_content.aggregate(pipeline).to_list(1)
        average_score = avg_result[0]['avgScore'] if avg_result else 0.0

        # By source statistics
        source_pipeline = [
            {'$group': {
                '_id': '$sourceName',
                'count': {'$sum': 1},
                'submitted': {
                    '$sum': {
                        '$cond': [{'$eq': ['$status', 'submitted']}, 1, 0]
                    }
                }
            }},
            {'$sort': {'count': -1}},
            {'$limit': 10}
        ]
        by_source = await db.extracted_content.aggregate(source_pipeline).to_list(10)
        by_source_formatted = [
            {
                'name': item['_id'],
                'count': item['count'],
                'submitted': item['submitted']
            }
            for item in by_source
        ]

        # Submission statistics
        total_submitted = status_counts.get('submitted', 0)
        total_attempts = total_submitted + status_counts.get('failed', 0)
        success_rate = (total_submitted / total_attempts * 100) if total_attempts > 0 else 0.0

        # Last submission
        last_submission = await db.extracted_content.find_one(
            {'status': 'submitted'},
            sort=[('submittedToAletheiaAt', -1)]
        )
        last_submission_time = last_submission['submittedToAletheiaAt'] if last_submission else None

        # Source statistics
        active_sources = await db.source_configuration.count_documents({'isActive': True})

        sources_list = await db.source_configuration.find(
            {'isActive': True},
            {'name': 1, 'lastExtraction': 1}
        ).sort('lastExtraction', -1).limit(10).to_list(10)

        last_extraction_times = [
            {
                'name': source['name'],
                'lastExtraction': source.get('lastExtraction')
            }
            for source in sources_list
        ]

        return {
            'extraction': {
                'totalToday': total_today,
                'totalByStatus': status_counts,
                'averageScore': round(average_score, 2),
                'bySource': by_source_formatted
            },
            'submission': {
                'totalSubmitted': total_submitted,
                'successRate': round(success_rate, 2),
                'lastSubmission': last_submission_time
            },
            'sources': {
                'active': active_sources,
                'lastExtractionTimes': last_extraction_times
            }
        }

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
