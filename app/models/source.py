"""SourceConfiguration model for managing RSS and HTML sources"""
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class CredibilityLevel(str, Enum):
    """Credibility classification for sources"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceType(str, Enum):
    """Source extraction type"""
    RSS = "rss"
    HTML = "html"
    API = "api"  # Future use


class SourceConfiguration(BaseModel):
    """Model for RSS and HTML source configuration"""

    name: str = Field(..., description="Display name of the source")
    sourceType: SourceType = Field(default=SourceType.RSS, description="Type of source (rss, html, api)")

    # RSS-specific fields
    rssUrl: Optional[str] = Field(None, description="RSS feed URL (required if sourceType=rss)")

    # HTML-specific fields
    htmlUrl: Optional[str] = Field(None, description="HTML page URL (required if sourceType=html)")
    htmlConfig: Optional[Dict[str, Any]] = Field(None, description="HTML scraping configuration")

    # Common fields
    isActive: bool = Field(default=True, description="Enable/disable extraction")
    credibilityLevel: CredibilityLevel = Field(..., description="Source credibility classification")
    lastExtraction: Optional[datetime] = Field(None, description="Last successful extraction")
    totalExtracted: int = Field(default=0, description="Total articles extracted")
    totalSubmitted: int = Field(default=0, description="Total articles submitted")
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "G1",
                "rssUrl": "https://g1.globo.com/rss/g1/",
                "isActive": True,
                "credibilityLevel": "high",
                "totalExtracted": 0,
                "totalSubmitted": 0
            }
        }
