"""AletheiaFact API client with OAuth2 authentication via Ory Hydra"""
import httpx
from datetime import datetime
from typing import Dict
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.services.ory_auth import ory_auth

logger = logging.getLogger(__name__)


class AletheiaClient:
    """Client for interacting with AletheiaFact API using OAuth2"""

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize AletheiaFact client.

        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.base_url = settings.aletheia_base_url
        self.ory_auth = ory_auth

    async def create_verification_request(self, content: Dict) -> Dict:
        """
        Submit content as a verification request to AletheiaFact.

        Uses OAuth2 Client Credentials flow via Ory Hydra for authentication.

        Args:
            content: Extracted content dictionary

        Returns:
            Verification request response

        Raises:
            Exception: If submission fails
        """
        # Get OAuth2 access token
        try:
            access_token = await self.ory_auth.get_access_token()
        except Exception as e:
            logger.error(f"Failed to get OAuth2 access token: {e}")
            raise Exception(f"OAuth2 authentication failed: {e}")

        impact_area = self._extract_impact_area(content)

        report_type = "Unattributed"

        payload = {
            "content": content['content'],
            "receptionChannel": "automated_monitoring",
            "reportType": report_type,
            "impactArea": impact_area,  # Can be string or {label, value}
            "source": [{"href": content['sourceUrl']}] if content.get('sourceUrl') else None,
            "publicationDate": content['publishedAt'].isoformat() if content.get('publishedAt') else None,
            "date": content['extractedAt'].isoformat(),
            "heardFrom": f"Automated Monitoring - {content['sourceName']}",
        }

        # Add recaptcha token if configured (required by API)
        if settings.recaptcha_token:
            payload["recaptcha"] = settings.recaptcha_token

        # Remove None values to avoid validation errors
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/verification-request",
                    json=payload,
                    headers={
                        'Authorization': f'Bearer {access_token}',  # OAuth2 token
                        'Content-Type': 'application/json'
                    },
                    timeout=30.0
                )

                response.raise_for_status()
                result = response.json()

                logger.info(f"Successfully created verification request: {result.get('_id', 'unknown')}")
                return result

        except httpx.HTTPStatusError as e:
            error_msg = f"VR creation failed: {e.response.status_code}"
            try:
                error_detail = e.response.json()
                error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {e.response.text}"

            logger.error(error_msg)
            raise Exception(error_msg)

        except Exception as e:
            logger.error(f"Error creating verification request: {e}")
            raise

    def _extract_impact_area(self, content: Dict) -> Dict:
        """
        Extract impact area from content using keyword matching.

        Args:
            content: Content dictionary

        Returns:
            Impact area object
        """
        text = content['content'].lower()

        political_kw = ["governo", "presidente", "ministro", "eleição", "congresso", "senado"]
        health_kw = ["vacina", "covid", "saúde", "hospital", "médico", "doença"]
        science_kw = ["cientista", "pesquisa", "estudo", "universidade", "descoberta"]

        if any(kw in text for kw in political_kw):
            return {"label": "Politics", "value": "politics"}
        elif any(kw in text for kw in health_kw):
            return {"label": "Health", "value": "health"}
        elif any(kw in text for kw in science_kw):
            return {"label": "Science", "value": "science"}
        else:
            return {"label": "General", "value": "general"}

