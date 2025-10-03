"""URL normalization utilities for deduplication"""
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


# Common tracking parameters to remove
TRACKING_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
    'fbclid', 'gclid', 'msclkid',  # Social/ad tracking
    'ref', 'source', 'campaign',    # Generic tracking
    '_ga', '_gl',                   # Google Analytics
}


def normalize_url(url: str) -> str:
    """
    Normalize URL by removing tracking parameters and standardizing format.

    This helps identify duplicate content that may have different tracking
    parameters in the URL.

    Args:
        url: Raw URL from RSS feed

    Returns:
        Normalized URL without tracking parameters

    Examples:
        >>> normalize_url("https://site.com/article?utm_source=rss&id=123")
        'https://site.com/article?id=123'

        >>> normalize_url("http://site.com/news")
        'https://site.com/news'
    """
    if not url:
        return url

    try:
        # Parse URL components
        parsed = urlparse(url)

        # Upgrade http to https (most news sites support https)
        scheme = 'https' if parsed.scheme == 'http' else parsed.scheme

        # Parse query parameters
        query_params = parse_qs(parsed.query, keep_blank_values=False)

        # Remove tracking parameters
        clean_params = {
            k: v for k, v in query_params.items()
            if k.lower() not in TRACKING_PARAMS
        }

        # Rebuild query string (sorted for consistency)
        clean_query = urlencode(sorted(clean_params.items()), doseq=True)

        # Reconstruct URL
        normalized = urlunparse((
            scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            clean_query,
            ''  # Remove fragment (e.g., #section)
        ))

        return normalized

    except Exception:
        # If parsing fails, return original URL
        return url
