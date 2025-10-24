"""HTML-based content extraction using BeautifulSoup and httpx"""
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
import httpx

from app.extractors.base_extractor import BaseExtractor
from app.utils.hash import generate_content_hash
from app.utils.url_normalizer import normalize_url
from app.filters.pre_filter import PreFilter
from app.nlp.claim_extractor import extract_checkable_content
from app.models.extracted_content import ContentStatus
from app.config import settings

logger = logging.getLogger(__name__)


class HTMLExtractor(BaseExtractor):
    """Extract content from HTML pages

    Inherits shared functionality from BaseExtractor for content saving
    and source statistics updates.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize HTML extractor.

        Args:
            db: MongoDB database instance
        """
        super().__init__(db)
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

            # Limit number of articles to process (prevent timeout when following links)
            max_articles = config.get('maxArticles', 20)
            articles = articles[:max_articles]

            logger.info(f"Found {len(articles)} article elements on page (processing up to {max_articles})")

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
        follow_links = config.get('followLinks', False)

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

        # Extract title from listing page
        title_selector = selectors.get('title', 'h3')
        title_elem = article_element.select_one(title_selector)
        title = title_elem.get_text(strip=True) if title_elem else ''

        if not title:
            logger.debug(f"No title found for URL: {url}")
            return None

        # Two-step extraction: follow link to get full content
        if follow_links:
            logger.debug(f"Following link to extract full content: {url}")
            full_article_data = await self._extract_full_article(url, title, source, config)
            if full_article_data:
                return full_article_data
            else:
                # If full extraction fails, fall back to excerpt extraction
                logger.debug(f"Full extraction failed, falling back to excerpt for: {url}")

        # Extract excerpt/content from listing page (fallback or default)
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

    async def _extract_full_article(self, url: str, title: str, source: Dict, config: Dict) -> Optional[Dict]:
        """
        Extract full content from individual article page.

        Args:
            url: Article URL
            title: Article title from listing page
            source: Source configuration
            config: HTML configuration

        Returns:
            Complete article data dict or None if extraction fails
        """
        try:
            article_page_config = config.get('articlePage', {})

            # Fetch article page
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; NewsMonitor/1.0)'}
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                article_html = response.text

            # Parse article page
            soup = BeautifulSoup(article_html, 'html.parser')

            # Extract full content body
            content_selector = article_page_config.get('contentSelector', '.w-richtext')
            content_elem = soup.select_one(content_selector)

            if not content_elem:
                logger.debug(f"No content found with selector '{content_selector}' on: {url}")
                return None

            # Extract all text from content element
            raw_content = content_elem.get_text(separator=' ', strip=True)

            # Extract fact-checkable content (allow more chars for full articles)
            max_chars = article_page_config.get('maxChars', 2000)
            content = extract_checkable_content(raw_content, max_chars=max_chars)

            if len(content) < 100:
                logger.debug(f"Full article content too short ({len(content)} chars): {url}")
                return None

            # Language detection
            from langdetect import detect, LangDetectException
            try:
                language = detect(content[:500])
                if language != 'pt':
                    logger.debug(f"Non-Portuguese content detected ({language}): {url}")
                    return None
            except LangDetectException:
                language = 'pt'

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
                    f"Full article score ({score_breakdown['total']}) below minimum ({settings.minimum_save_score}), "
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
                'publishedAt': None,
                'language': language,
                'preFilterScore': score_breakdown['total'],
                'status': status,
                'contentHash': content_hash,
                'createdAt': datetime.utcnow(),
                'updatedAt': datetime.utcnow()
            }

        except httpx.HTTPError as e:
            logger.warning(f"HTTP error fetching full article {url}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error extracting full article {url}: {e}")
            return None
