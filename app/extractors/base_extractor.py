"""Base extractor class with shared functionality for all extractors"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError
import logging

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Abstract base class for content extractors

    Provides shared functionality for saving content and updating source statistics.
    All concrete extractors (RSS, HTML, API) should inherit from this class.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize base extractor.

        Args:
            db: MongoDB database instance
        """
        self.db = db

    @abstractmethod
    async def extract_from_source(self, source: Dict) -> int:
        """
        Extract content from a single source.

        Must be implemented by concrete extractor classes.

        Args:
            source: Source configuration dictionary

        Returns:
            Number of new articles extracted
        """
        pass

    async def _save_content(self, content_dict: Dict) -> bool:
        """
        Save extracted content to database.

        Shared implementation across all extractors to ensure consistency
        in content storage and duplicate handling.

        Args:
            content_dict: Content dictionary with all required fields

        Returns:
            True if saved successfully, False if duplicate
        """
        try:
            await self.db.extracted_content.insert_one(content_dict)
            logger.debug(f"Saved content: {content_dict['title'][:50]}...")
            return True

        except DuplicateKeyError:
            logger.debug(f"Duplicate content detected: {content_dict['contentHash']}")
            return False

        except Exception as e:
            logger.error(f"Error saving content: {e}")
            return False

    async def _update_source_stats(self, source: Dict, extracted_count: int):
        """
        Update source statistics after extraction.

        Shared implementation to maintain consistent source tracking
        across all extractor types.

        Args:
            source: Source configuration dictionary with _id
            extracted_count: Number of articles successfully extracted
        """
        try:
            await self.db.source_configuration.update_one(
                {'_id': source['_id']},
                {
                    '$set': {
                        'lastExtraction': datetime.utcnow(),
                        'updatedAt': datetime.utcnow()
                    },
                    '$inc': {
                        'totalExtracted': extracted_count
                    }
                }
            )
            logger.debug(f"Updated stats for {source['name']}: +{extracted_count} extracted")

        except Exception as e:
            logger.error(f"Error updating source stats for {source.get('name', 'unknown')}: {e}")
