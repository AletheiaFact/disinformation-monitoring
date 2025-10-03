"""MongoDB database connection and setup"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING, DESCENDING
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class Database:
    """MongoDB database manager"""

    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

    async def connect(self):
        """Connect to MongoDB and setup indexes"""
        try:
            self.client = AsyncIOMotorClient(settings.mongodb_url)
            self.db = self.client[settings.database_name]

            # Test connection
            await self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB: {settings.database_name}")

            # Setup indexes
            await self._setup_indexes()

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    async def _setup_indexes(self):
        """Create database indexes for optimal performance"""

        # ExtractedContent indexes
        content_indexes = [
            IndexModel([("contentHash", ASCENDING)], unique=True),
            IndexModel([("status", ASCENDING), ("extractedAt", DESCENDING)]),
            IndexModel([("preFilterScore", DESCENDING)]),
            IndexModel([("sourceName", ASCENDING)]),
            IndexModel([("createdAt", DESCENDING)]),
        ]
        await self.db.extracted_content.create_indexes(content_indexes)

        # SourceConfiguration indexes
        source_indexes = [
            IndexModel([("isActive", ASCENDING)]),
            IndexModel([("lastExtraction", DESCENDING)]),
            IndexModel([("rssUrl", ASCENDING)], unique=True),
        ]
        await self.db.source_configuration.create_indexes(source_indexes)

        logger.info("Database indexes created successfully")


# Global database instance
database = Database()


async def get_database() -> AsyncIOMotorDatabase:
    """Dependency for FastAPI routes to get database instance"""
    return database.db
