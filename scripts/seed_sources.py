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
    # High Credibility (4 sources)
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
        "name": "BBC Brasil",
        "rssUrl": "https://feeds.bbci.co.uk/portuguese/rss.xml",
        "credibilityLevel": "high",
        "isActive": True
    },
    {
        "name": "Estado de S.Paulo",
        "rssUrl": "https://www.estadao.com.br/rss/brasil.xml",
        "credibilityLevel": "high",
        "isActive": True
    },

    # Medium Credibility (6 sources)
    {
        "name": "CNN Brasil",
        "rssUrl": "https://www.cnnbrasil.com.br/feed/",
        "credibilityLevel": "medium",
        "isActive": True
    },
    {
        "name": "Poder360",
        "rssUrl": "https://www.poder360.com.br/feed/",
        "credibilityLevel": "medium",
        "isActive": True
    },
    {
        "name": "CartaCapital",
        "rssUrl": "https://www.cartacapital.com.br/feed/",
        "credibilityLevel": "medium",
        "isActive": True
    },
    {
        "name": "Gazeta do Povo",
        "rssUrl": "https://www.gazetadopovo.com.br/feed/rss/republica.xml",
        "credibilityLevel": "medium",
        "isActive": True
    },
    {
        "name": "Metrópoles",
        "rssUrl": "https://www.metropoles.com/feed",
        "credibilityLevel": "medium",
        "isActive": True
    },
    {
        "name": "The Intercept Brasil",
        "rssUrl": "https://www.intercept.com.br/feed/",
        "credibilityLevel": "medium",
        "isActive": True
    },

    # Low Credibility (5 sources - PRIORITY for misinformation monitoring)
    {
        "name": "Terça Livre",
        "rssUrl": "https://tercalivre.com.br/feed/",
        "credibilityLevel": "low",
        "isActive": True
    },
    {
        "name": "Jornal da Cidade Online",
        "rssUrl": "https://www.jornaldacidadeonline.com.br/noticias/feed",
        "credibilityLevel": "low",
        "isActive": True
    },
    {
        "name": "Brasil 247",
        "rssUrl": "https://www.brasil247.com/feed",
        "credibilityLevel": "low",
        "isActive": True
    },
    {
        "name": "Conexão Política",
        "rssUrl": "https://www.conexaopolitica.com.br/feed/",
        "credibilityLevel": "low",
        "isActive": True
    },
    {
        "name": "DCM",
        "rssUrl": "https://www.diariodocentrodomundo.com.br/feed/",
        "credibilityLevel": "low",
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
