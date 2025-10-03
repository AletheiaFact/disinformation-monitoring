"""ExtractedContent model for storing extracted news articles"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class ContentStatus(str, Enum):
    """Status of extracted content"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    REJECTED = "rejected"
    FAILED = "failed"


class ExtractedContent(BaseModel):
    """Model for extracted content from RSS feeds"""

    sourceUrl: str = Field(..., description="Original article URL")
    sourceName: str = Field(..., description="Source name (e.g., 'G1')")
    content: str = Field(..., description="Main text content")
    title: str = Field(..., description="Article title")
    extractedAt: datetime = Field(default_factory=datetime.utcnow, description="When we extracted it")
    publishedAt: Optional[datetime] = Field(None, description="Original publication date")
    language: str = Field(..., description="ISO 639-1 code (pt, es, en)")
    preFilterScore: int = Field(..., description="Score from pre-filter (0-60)")
    status: ContentStatus = Field(default=ContentStatus.PENDING, description="Processing status")
    contentHash: str = Field(..., description="SHA-256 hash for deduplication")

    # AletheiaFact Integration
    verificationRequestId: Optional[str] = Field(None, description="VR ID from AletheiaFact")
    submittedToAletheiaAt: Optional[datetime] = Field(None, description="Timestamp of submission")
    submissionError: Optional[str] = Field(None, description="Error message if submission failed")

    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "sourceUrl": "https://g1.globo.com/politica/noticia/2025/01/15/exemplo.ghtml",
                "sourceName": "G1",
                "content": "Texto completo da notícia...",
                "title": "Título da Notícia",
                "language": "pt",
                "preFilterScore": 45,
                "status": "pending",
                "contentHash": "abc123..."
            }
        }
