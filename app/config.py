"""Configuration management using Pydantic Settings"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # MongoDB Configuration
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "monitoring_poc"

    # Logging
    log_level: str = "info"

    # AletheiaFact API
    aletheia_base_url: str = "http://localhost:3000"

    # Ory Cloud OAuth2 (Client Credentials Flow)
    ory_cloud_url: str = "https://your-project-slug.projects.oryapis.com"
    ory_client_id: Optional[str] = None
    ory_client_secret: Optional[str] = None
    ory_scope: str = "openid offline_access"

    # Recaptcha
    recaptcha_token: Optional[str] = None

    # Scheduler
    extraction_interval_minutes: int = 30

    # Filtering and Submission
    minimum_save_score: int = 20  # Minimum score to save content to database
    submission_score_threshold: int = 35  # Minimum score to submit to AletheiaFact
    max_batch_submission: int = 100
    auto_submit_enabled: bool = False  # Enable/disable automatic submission to AletheiaFact

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
