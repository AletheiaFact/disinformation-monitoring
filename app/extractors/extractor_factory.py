"""Factory to create appropriate extractor based on source type"""
from app.models.source import SourceType
from app.extractors.rss_extractor import RSSExtractor
from app.extractors.html_extractor import HTMLExtractor
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class ExtractorFactory:
    """Factory for creating extractors based on source type"""

    @staticmethod
    def get_extractor(source_type: SourceType, db: AsyncIOMotorDatabase):
        """
        Get appropriate extractor for source type.

        Args:
            source_type: Type of source (RSS, HTML, API)
            db: Database instance

        Returns:
            Extractor instance

        Raises:
            ValueError: If source type is not supported
        """
        if source_type == SourceType.RSS:
            return RSSExtractor(db)
        elif source_type == SourceType.HTML:
            return HTMLExtractor(db)
        elif source_type == SourceType.API:
            raise NotImplementedError("API extraction not yet implemented")
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

    @staticmethod
    async def extract_from_source(source: Dict, db: AsyncIOMotorDatabase) -> int:
        """
        Extract from any source type using appropriate extractor.

        Args:
            source: Source configuration dictionary
            db: Database instance

        Returns:
            Number of articles extracted
        """
        source_type = SourceType(source.get('sourceType', 'rss'))

        logger.debug(f"Using {source_type.value} extractor for {source['name']}")

        extractor = ExtractorFactory.get_extractor(source_type, db)
        return await extractor.extract_from_source(source)
