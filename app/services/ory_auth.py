"""OAuth2 authentication service using Ory Hydra with Client Credentials flow"""
import httpx
import asyncio
import time
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class OryAuthService:
    """Service for handling OAuth2 authentication with Ory Hydra"""

    def __init__(self):
        self.ory_cloud_url = settings.ory_cloud_url
        self.client_id = settings.ory_client_id
        self.client_secret = settings.ory_client_secret
        self.scope = settings.ory_scope

        # Token caching
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._token_lock = asyncio.Lock()

    async def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.

        Returns:
            Valid OAuth2 access token

        Raises:
            Exception: If token generation fails
        """
        async with self._token_lock:
            if self._is_token_valid():
                logger.debug("Using cached OAuth2 token")
                return self._access_token

            logger.info("Generating new OAuth2 access token")
            return await self._generate_client_credentials_token()

    def _is_token_valid(self) -> bool:
        """
        Check if current token is valid and not expired.

        Returns:
            True if token is valid and has >60s before expiry
        """
        if not self._access_token or not self._token_expires_at:
            return False

        # Add 60 second buffer before expiry
        return datetime.utcnow() < (self._token_expires_at - timedelta(seconds=60))

    async def _generate_client_credentials_token(self) -> str:
        """
        Generate access token using client credentials flow (machine-to-machine).

        Returns:
            Access token string

        Raises:
            Exception: If token generation fails
        """
        # Use Basic Authentication (client_secret_basic)
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        form_data = {
            "grant_type": "client_credentials",
            "scope": self.scope,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}"
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                start_time = time.time()
                response = await client.post(
                    f"{self.ory_cloud_url}/oauth2/token",
                    headers=headers,
                    data=form_data
                )

                duration = time.time() - start_time
                logger.info(
                    f"OAuth2 token request completed in {duration:.2f}s",
                    extra={
                        "endpoint": "/oauth2/token",
                        "method": "POST",
                        "status_code": response.status_code,
                        "duration": duration
                    }
                )

                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(
                        "Failed to generate OAuth2 token",
                        extra={
                            "status_code": response.status_code,
                            "response": error_detail
                        }
                    )
                    raise Exception(f"OAuth2 token generation failed: {response.status_code} - {error_detail}")

                token_data = response.json()

                # Cache the token
                self._access_token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
                self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

                logger.info(
                    "Successfully generated OAuth2 token",
                    extra={
                        "expires_in": expires_in,
                        "token_type": token_data.get("token_type", "bearer"),
                        "expires_at": self._token_expires_at.isoformat()
                    }
                )

                return self._access_token

        except httpx.TimeoutException:
            logger.error("Timeout while generating OAuth2 token")
            raise Exception("OAuth2 token generation timeout")
        except httpx.RequestError as e:
            logger.error(f"Network error while generating OAuth2 token: {e}")
            raise Exception(f"OAuth2 token generation network error: {e}")
        except Exception as e:
            logger.error(f"Error generating OAuth2 token: {e}")
            raise

    def clear_cache(self):
        """Clear cached token (useful for testing or forced refresh)"""
        self._access_token = None
        self._token_expires_at = None
        logger.info("OAuth2 token cache cleared")


# Global singleton instance
ory_auth = OryAuthService()
