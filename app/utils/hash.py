"""SHA-256 hashing utilities for content deduplication"""
import hashlib


def generate_content_hash(url: str, content: str) -> str:
    """
    Generate SHA-256 hash for content deduplication.

    Args:
        url: Source URL of the content
        content: Main text content

    Returns:
        Hexadecimal SHA-256 hash string
    """
    # Normalize content by removing extra whitespace
    normalized_content = " ".join(content.split())

    # Combine URL and content for unique hash
    combined = f"{url}|{normalized_content}"

    # Generate SHA-256 hash
    hash_object = hashlib.sha256(combined.encode('utf-8'))
    return hash_object.hexdigest()
