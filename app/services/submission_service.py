"""Service for submitting content to AletheiaFact"""
from datetime import datetime
from typing import Dict, Optional
from bson import ObjectId
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.clients.aletheia_client import AletheiaClient
from app.models.extracted_content import ContentStatus
from app.config import settings

logger = logging.getLogger(__name__)


class SubmissionService:
    """Handle submission of content to AletheiaFact"""

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize submission service.

        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.aletheia_client = AletheiaClient(db)

    async def submit_content(self, content_id: str) -> bool:
        """
        Submit a single content item to AletheiaFact.

        Args:
            content_id: MongoDB ObjectId of content to submit

        Returns:
            True if submission successful, False otherwise
        """
        try:
            # Fetch content from database
            content = await self.db.extracted_content.find_one({
                '_id': ObjectId(content_id)
            })

            if not content:
                logger.error(f"Content not found: {content_id}")
                return False

            # Verify not already submitted
            if content['status'] == ContentStatus.SUBMITTED:
                logger.warning(f"Content already submitted: {content_id}")
                return False

            # Verify score meets threshold
            if content['preFilterScore'] < settings.submission_score_threshold:
                logger.warning(
                    f"Content score ({content['preFilterScore']}) below threshold "
                    f"({settings.submission_score_threshold}): {content_id}"
                )
                await self._update_content_status(
                    content_id,
                    ContentStatus.REJECTED,
                    error="Score below submission threshold"
                )
                return False

            # Attempt submission to AletheiaFact
            try:
                vr_response = await self.aletheia_client.create_verification_request(content)

                # Extract VR ID from response
                vr_id = vr_response.get('_id') or vr_response.get('id')

                # Update content status to submitted
                await self.db.extracted_content.update_one(
                    {'_id': ObjectId(content_id)},
                    {
                        '$set': {
                            'status': ContentStatus.SUBMITTED,
                            'verificationRequestId': vr_id,
                            'submittedToAletheiaAt': datetime.utcnow(),
                            'submissionError': None,
                            'updatedAt': datetime.utcnow()
                        }
                    }
                )

                # Update source statistics
                await self._increment_source_submitted(content['sourceName'])

                logger.info(f"Successfully submitted content {content_id} as VR {vr_id}")
                return True

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Submission failed for content {content_id}: {error_msg}")

                # Update content status to failed
                await self._update_content_status(
                    content_id,
                    ContentStatus.FAILED,
                    error=error_msg
                )
                return False

        except Exception as e:
            logger.error(f"Error in submit_content for {content_id}: {e}")
            return False

    async def submit_pending_content(self, limit: Optional[int] = None) -> Dict[str, int]:
        """
        Submit all pending content that meets submission criteria.

        Args:
            limit: Maximum number of items to submit (default: from settings)

        Returns:
            Dictionary with submission statistics
        """
        if limit is None:
            limit = settings.max_batch_submission

        try:
            # Find all pending content with sufficient score
            query = {
                'status': ContentStatus.PENDING,
                'preFilterScore': {'$gte': settings.submission_score_threshold}
            }

            pending_content = await self.db.extracted_content.find(query).limit(limit).to_list(None)

            logger.info(f"Found {len(pending_content)} pending items to submit")

            successful = 0
            failed = 0

            for content in pending_content:
                content_id = str(content['_id'])
                success = await self.submit_content(content_id)

                if success:
                    successful += 1
                else:
                    failed += 1

            logger.info(f"Batch submission complete: {successful} successful, {failed} failed")

            return {
                'total': len(pending_content),
                'successful': successful,
                'failed': failed
            }

        except Exception as e:
            logger.error(f"Error in submit_pending_content: {e}")
            return {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'error': str(e)
            }

    async def _update_content_status(
        self,
        content_id: str,
        status: ContentStatus,
        error: Optional[str] = None
    ):
        """
        Update content status and error message.

        Args:
            content_id: Content ID
            status: New status
            error: Optional error message
        """
        update_data = {
            'status': status,
            'updatedAt': datetime.utcnow()
        }

        if error:
            update_data['submissionError'] = error

        await self.db.extracted_content.update_one(
            {'_id': ObjectId(content_id)},
            {'$set': update_data}
        )

    async def _increment_source_submitted(self, source_name: str):
        """
        Increment the submitted counter for a source.

        Args:
            source_name: Name of the source
        """
        try:
            await self.db.source_configuration.update_one(
                {'name': source_name},
                {
                    '$inc': {'totalSubmitted': 1},
                    '$set': {'updatedAt': datetime.utcnow()}
                }
            )
        except Exception as e:
            logger.error(f"Error incrementing source submitted count: {e}")
