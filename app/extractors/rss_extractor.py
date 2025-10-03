"""RSS feed extraction logic with sentence-level fact-checkable content extraction"""
import feedparser
from bs4 import BeautifulSoup
from langdetect import detect, LangDetectException
from datetime import datetime
from typing import Dict, List, Optional
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.utils.hash import generate_content_hash
from app.utils.url_normalizer import normalize_url
from app.filters.pre_filter import PreFilter
from app.models.extracted_content import ExtractedContent, ContentStatus
from app.config import settings
from app.nlp.claim_extractor import extract_checkable_content

logger = logging.getLogger(__name__)


class RSSExtractor:
    """Extract content from RSS feeds"""

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize RSS extractor.

        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.pre_filter = PreFilter()

    async def extract_from_source(self, source: Dict) -> int:
        """
        Extract content from a single RSS source.

        Args:
            source: Source configuration dictionary

        Returns:
            Number of new articles extracted
        """
        try:
            logger.info(f"Extracting from source: {source['name']}")

            # Fetch RSS feed
            feed = feedparser.parse(source['rssUrl'])

            if feed.bozo:
                logger.warning(f"RSS feed parsing warning for {source['name']}: {feed.bozo_exception}")

            extracted_count = 0

            # Process each entry
            for entry in feed.entries:
                try:
                    # Extract content from entry
                    content_dict = await self._extract_entry(entry, source)

                    if content_dict:
                        # Try to save to database
                        saved = await self._save_content(content_dict)
                        if saved:
                            extracted_count += 1

                except Exception as e:
                    logger.error(f"Error processing entry from {source['name']}: {e}")
                    continue

            # Update source statistics
            await self._update_source_stats(source, extracted_count)

            logger.info(f"Extracted {extracted_count} new articles from {source['name']}")
            return extracted_count

        except Exception as e:
            logger.error(f"Error extracting from source {source['name']}: {e}")
            return 0

    async def _extract_entry(self, entry: Dict, source: Dict) -> Optional[Dict]:
        """
        Extract and process a single RSS entry.

        Args:
            entry: RSS feed entry
            source: Source configuration

        Returns:
            Processed content dictionary or None if invalid
        """
        # Extract URL
        url = entry.get('link', '')
        if not url:
            logger.debug("Entry missing URL, skipping")
            return None

        # Normalize URL (remove tracking params, upgrade to https)
        url = normalize_url(url)

        # Early duplicate check - skip if URL already processed
        # This avoids expensive NLP processing for duplicates
        existing = await self.db.extracted_content.find_one(
            {'sourceUrl': url},
            {'_id': 1}  # Only fetch ID for speed
        )
        if existing:
            logger.debug(f"URL already processed, skipping: {url}")
            return None

        # Extract title
        title = entry.get('title', '').strip()
        if not title:
            logger.debug(f"Entry missing title: {url}")
            return None

        # Extract content (try multiple fields)
        raw_content = (
            entry.get('content', [{}])[0].get('value', '') or
            entry.get('summary', '') or
            entry.get('description', '')
        )

        if not raw_content:
            logger.debug(f"Entry missing content: {url}")
            return None

        # Extract fact-checkable content using sentence-level scoring
        content = extract_checkable_content(raw_content, max_chars=500)

        # Minimum content length check (after extraction)
        if len(content) < 50:
            logger.debug(f"No fact-checkable content extracted or too short: {url}")
            return None

        # Detect language
        language = self._detect_language(content)
        if language != 'pt':
            logger.debug(f"Non-Portuguese content detected ({language}): {url}")
            return None

        # Extract published date
        published_at = self._parse_date(entry)

        # Generate content hash for deduplication
        content_hash = generate_content_hash(url, content)

        # Calculate pre-filter score
        score_breakdown = self.pre_filter.calculate_score(
            content=content,
            title=title,
            source_url=url,
            credibility_level=source['credibilityLevel']
        )

        # Skip content with score below minimum threshold
        if score_breakdown['total'] < settings.minimum_save_score:
            logger.debug(
                f"Content score ({score_breakdown['total']}) below minimum ({settings.minimum_save_score}), "
                f"skipping: {title[:50]}..."
            )
            return None

        # Determine initial status
        status = ContentStatus.PENDING if score_breakdown['total'] >= settings.submission_score_threshold else ContentStatus.REJECTED

        return {
            'sourceUrl': url,
            'sourceName': source['name'],
            'content': content,
            'title': title,
            'extractedAt': datetime.utcnow(),
            'publishedAt': published_at,
            'language': language,
            'preFilterScore': score_breakdown['total'],
            'status': status,
            'contentHash': content_hash,
            'createdAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow()
        }

    def _detect_language(self, text: str) -> str:
        """
        Detect language of text content.

        Args:
            text: Text content

        Returns:
            ISO 639-1 language code (e.g., 'pt', 'en')
        """
        try:
            # Use first 500 characters for detection
            sample = text[:500]
            return detect(sample)
        except LangDetectException:
            logger.debug("Language detection failed, defaulting to 'pt'")
            return 'pt'
        except Exception as e:
            logger.warning(f"Language detection error: {e}")
            return 'unknown'

    def _parse_date(self, entry: Dict) -> Optional[datetime]:
        """
        Parse published date from RSS entry.

        Args:
            entry: RSS feed entry

        Returns:
            Datetime object or None
        """
        # Try different date fields
        date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']

        for field in date_fields:
            if field in entry and entry[field]:
                try:
                    time_struct = entry[field]
                    return datetime(*time_struct[:6])
                except Exception as e:
                    logger.debug(f"Error parsing date from {field}: {e}")
                    continue

        return None

    async def _save_content(self, content_dict: Dict) -> bool:
        """
        Save extracted content to database.

        Args:
            content_dict: Content dictionary

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

        Args:
            source: Source configuration
            extracted_count: Number of articles extracted
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
        except Exception as e:
            logger.error(f"Error updating source stats: {e}")


async def extract_all_sources(db: AsyncIOMotorDatabase) -> Dict[str, int]:
    """
    Extract content from all active sources.

    Args:
        db: MongoDB database instance

    Returns:
        Dictionary with extraction statistics
    """
    extractor = RSSExtractor(db)

    # Get all active sources
    sources = await db.source_configuration.find({'isActive': True}).to_list(None)

    total_extracted = 0
    source_results = {}

    for source in sources:
        count = await extractor.extract_from_source(source)
        total_extracted += count
        source_results[source['name']] = count

    logger.info(f"Total extraction complete: {total_extracted} articles from {len(sources)} sources")

    return {
        'totalExtracted': total_extracted,
        'sourceCount': len(sources),
        'bySource': source_results
    }
