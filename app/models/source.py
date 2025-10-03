"""SourceConfiguration model for managing RSS feed sources"""
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import Optional
from enum import Enum


class CredibilityLevel(str, Enum):
    """Credibility classification for sources"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceConfiguration(BaseModel):
    """Model for RSS feed source configuration"""

    name: str = Field(..., description="Display name of the source")
    rssUrl: str = Field(..., description="RSS feed URL")
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
