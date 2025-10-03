"""Seed initial RSS sources into the database"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

# Initial RSS sources for Brazilian news monitoring
SOURCES = [
    {
        "name": "G1",
        "rssUrl": "https://g1.globo.com/rss/g1/",
        "credibilityLevel": "high",
        "isActive": True
    },
    {
        "name": "Folha de S.Paulo",
        "rssUrl": "https://feeds.folha.uol.com.br/folha/cotidiano/rss091.xml",
        "credibilityLevel": "high",
        "isActive": True
    },
    {
        "name": "O Globo",
        "rssUrl": "https://oglobo.globo.com/rss.xml",
        "credibilityLevel": "high",
        "isActive": True
    },
    {
        "name": "UOL Notícias",
        "rssUrl": "https://rss.uol.com.br/feed/noticias.xml",
        "credibilityLevel": "high",
        "isActive": True
    },
    {
        "name": "Estado de S.Paulo",
        "rssUrl": "https://politica.estadao.com.br/rss/ultimas.xml",
        "credibilityLevel": "high",
        "isActive": True
    },
    {
        "name": "R7 Notícias",
        "rssUrl": "https://noticias.r7.com/brasil/feed.xml",
        "credibilityLevel": "medium",
        "isActive": True
    },
    {
        "name": "CNN Brasil",
        "rssUrl": "https://www.cnnbrasil.com.br/feed/",
        "credibilityLevel": "high",
        "isActive": True
    },
    {
        "name": "BBC Brasil",
        "rssUrl": "https://feeds.bbci.co.uk/portuguese/rss.xml",
        "credibilityLevel": "high",
        "isActive": True
    },
    {
        "name": "CartaCapital",
        "rssUrl": "https://www.cartacapital.com.br/feed/",
        "credibilityLevel": "medium",
        "isActive": True
    },
    {
        "name": "Poder360",
        "rssUrl": "https://www.poder360.com.br/feed/",
        "credibilityLevel": "medium",
        "isActive": True
    }
]


async def seed_sources():
    """Seed initial RSS sources into the database"""

    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.database_name]

    print(f"Connected to MongoDB: {settings.database_name}")
    print(f"Seeding {len(SOURCES)} RSS sources...\n")

    inserted_count = 0
    skipped_count = 0

    for source_data in SOURCES:
        # Check if source already exists
        existing = await db.source_configuration.find_one({
            'rssUrl': source_data['rssUrl']
        })

        if existing:
            print(f"⊘ Skipping {source_data['name']} (already exists)")
            skipped_count += 1
            continue

        # Add timestamps
        source_data['totalExtracted'] = 0
        source_data['totalSubmitted'] = 0
        source_data['createdAt'] = datetime.utcnow()
        source_data['updatedAt'] = datetime.utcnow()

        # Insert source
        result = await db.source_configuration.insert_one(source_data)
        print(f"✓ Added {source_data['name']} ({source_data['credibilityLevel']})")
        inserted_count += 1

    print(f"\nSeeding complete!")
    print(f"  Inserted: {inserted_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Total: {len(SOURCES)}")

    # Close connection
    client.close()


if __name__ == "__main__":
    asyncio.run(seed_sources())
