"""HTML-based content extraction using BeautifulSoup and Selenium"""
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError
from datetime import datetime
import httpx

from app.utils.hash import generate_content_hash
from app.utils.url_normalizer import normalize_url
from app.filters.pre_filter import PreFilter
from app.nlp.claim_extractor import extract_checkable_content
from app.models.extracted_content import ContentStatus
from app.config import settings

logger = logging.getLogger(__name__)


class HTMLExtractor:
    """Extract content from HTML pages"""

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize HTML extractor.

        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.pre_filter = PreFilter()

    async def extract_from_source(self, source: Dict) -> int:
        """
        Extract content from HTML source using static extraction.

        Args:
            source: Source configuration with htmlConfig

        Returns:
            Number of new articles extracted
        """
        config = source.get('htmlConfig', {})
        return await self._extract_static(source, config)

    async def _extract_static(self, source: Dict, config: Dict) -> int:
        """Extract from static HTML using httpx + BeautifulSoup"""
        try:
            listing_url = config.get('listingUrl') or source.get('htmlUrl')

            logger.info(f"Extracting from HTML source: {source['name']}")

            # Fetch HTML
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; NewsMonitor/1.0)'}
            ) as client:
                response = await client.get(listing_url)
                response.raise_for_status()
                html = response.text

            # Parse HTML
            soup = BeautifulSoup(html, 'html.parser')
            article_selector = config.get('articleSelector', 'article')
            articles = soup.select(article_selector)

            logger.info(f"Found {len(articles)} article elements on page")

            extracted_count = 0

            for article in articles:
                try:
                    article_data = await self._parse_article(article, source, config)
                    if article_data:
                        saved = await self._save_content(article_data)
                        if saved:
                            extracted_count += 1
                except Exception as e:
                    logger.debug(f"Error parsing article: {e}")
                    continue

            # Update source statistics
            await self._update_source_stats(source, extracted_count)

            logger.info(f"Extracted {extracted_count} new articles from {source['name']}")
            return extracted_count

        except Exception as e:
            logger.error(f"Error extracting from HTML source {source['name']}: {e}")
            return 0

    async def _parse_article(self, article_element, source: Dict, config: Dict) -> Optional[Dict]:
        """Parse individual article element to extract data"""
        selectors = config.get('selectors', {})
        url_prefix = config.get('urlPrefix', '')

        # Extract URL
        url_selector = selectors.get('url', 'a')

        # Check if article element itself is a link
        if article_element.name == 'a':
            url_elem = article_element
        else:
            url_elem = article_element.select_one(url_selector)

        if not url_elem:
            logger.debug(f"No URL element found for article")
            return None

        raw_url = url_elem.get('href')
        if not raw_url:
            logger.debug(f"URL element has no href attribute")
            return None

        # Handle relative URLs
        if raw_url.startswith('/'):
            raw_url = url_prefix + raw_url
        elif not raw_url.startswith('http'):
            # Handle protocol-relative URLs
            if raw_url.startswith('//'):
                raw_url = 'https:' + raw_url
            else:
                raw_url = url_prefix + '/' + raw_url

        url = normalize_url(raw_url)

        # Early duplicate check
        existing = await self.db.extracted_content.find_one(
            {'sourceUrl': url},
            {'_id': 1}
        )
        if existing:
            logger.debug(f"URL already processed, skipping: {url}")
            return None

        # Extract title
        title_selector = selectors.get('title', 'h3')
        title_elem = article_element.select_one(title_selector)
        title = title_elem.get_text(strip=True) if title_elem else ''

        if not title:
            logger.debug(f"No title found for URL: {url}")
            return None

        # Extract excerpt/content
        excerpt_selector = selectors.get('excerpt', 'p, .excerpt')
        excerpt_elem = article_element.select_one(excerpt_selector)
        raw_content = excerpt_elem.get_text(strip=True) if excerpt_elem else title

        # Extract fact-checkable content
        content = extract_checkable_content(raw_content, max_chars=500)

        if len(content) < 50:
            logger.debug(f"Content too short after extraction: {url}")
            return None

        # Language detection
        from langdetect import detect, LangDetectException
        try:
            language = detect(content[:500])
            if language != 'pt':
                logger.debug(f"Non-Portuguese content detected ({language}): {url}")
                return None
        except LangDetectException:
            language = 'pt'  # Assume Portuguese if detection fails

        # Generate content hash
        content_hash = generate_content_hash(url, content)

        # Calculate pre-filter score
        score_breakdown = self.pre_filter.calculate_score(
            content=content,
            title=title,
            source_url=url,
            credibility_level=source['credibilityLevel']
        )

        # Skip low-scoring content
        if score_breakdown['total'] < settings.minimum_save_score:
            logger.debug(
                f"Content score ({score_breakdown['total']}) below minimum ({settings.minimum_save_score}), "
                f"skipping: {title[:50]}..."
            )
            return None

        # Determine status
        status = (
            ContentStatus.PENDING
            if score_breakdown['total'] >= settings.submission_score_threshold
            else ContentStatus.REJECTED
        )

        return {
            'sourceUrl': url,
            'sourceName': source['name'],
            'content': content,
            'title': title,
            'extractedAt': datetime.utcnow(),
            'publishedAt': None,  # HTML scraping often doesn't provide reliable dates
            'language': language,
            'preFilterScore': score_breakdown['total'],
            'status': status,
            'contentHash': content_hash,
            'createdAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow()
        }

    async def _save_content(self, content_dict: Dict) -> bool:
        """Save extracted content to database"""
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
        """Update source statistics after extraction"""
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
