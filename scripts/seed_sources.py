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
        "sourceType": "rss",
        "rssUrl": "https://g1.globo.com/rss/g1/",
        "credibilityLevel": "high",
        "isActive": True
    },
    {
        "name": "Folha de S.Paulo",
        "sourceType": "rss",
        "rssUrl": "https://feeds.folha.uol.com.br/folha/cotidiano/rss091.xml",
        "credibilityLevel": "high",
        "isActive": True
    },
    {
        "name": "BBC Brasil",
        "sourceType": "rss",
        "rssUrl": "https://feeds.bbci.co.uk/portuguese/rss.xml",
        "credibilityLevel": "high",
        "isActive": True
    },
    {
        "name": "Estado de S.Paulo",
        "sourceType": "rss",
        "rssUrl": "https://www.estadao.com.br/arc/outboundfeeds/feeds/rss/sections/politica/",
        "credibilityLevel": "high",
        "isActive": True
    },

    # Medium Credibility (6 sources)
    {
        "name": "CNN Brasil",
        "sourceType": "rss",
        "rssUrl": "https://www.cnnbrasil.com.br/feed/",
        "credibilityLevel": "medium",
        "isActive": True
    },
    {
        "name": "Poder360",
        "sourceType": "rss",
        "rssUrl": "https://www.poder360.com.br/feed/",
        "credibilityLevel": "medium",
        "isActive": True
    },
    {
        "name": "CartaCapital",
        "sourceType": "rss",
        "rssUrl": "https://www.cartacapital.com.br/feed/",
        "credibilityLevel": "medium",
        "isActive": True
    },
    {
        "name": "Gazeta do Povo",
        "sourceType": "rss",
        "rssUrl": "https://www.gazetadopovo.com.br/feed/rss/republica.xml",
        "credibilityLevel": "medium",
        "isActive": True
    },
    {
        "name": "Metrópoles",
        "sourceType": "rss",
        "rssUrl": "https://www.metropoles.com/feed",
        "credibilityLevel": "medium",
        "isActive": True
    },
    {
        "name": "The Intercept Brasil",
        "sourceType": "rss",
        "rssUrl": "https://www.intercept.com.br/feed/",
        "credibilityLevel": "medium",
        "isActive": True
    },

    # Low Credibility (5 sources - PRIORITY for misinformation monitoring)
    # {
    #     "name": "Terça Livre",
    #     "sourceType": "rss",
    #     "rssUrl": "https://tercalivre.com.br/feed/",
    #     "credibilityLevel": "low",
    #     "isActive": True
    # },
    # {
    #     "name": "Jornal da Cidade Online",
    #     "sourceType": "rss",
    #     "rssUrl": "https://www.jornaldacidadeonline.com.br/noticias/feed",
    #     "credibilityLevel": "low",
    #     "isActive": True
    # },
    # {
    #     "name": "Brasil 247",
    #     "sourceType": "rss",
    #     "rssUrl": "https://www.brasil247.com/feed",
    #     "credibilityLevel": "low",
    #     "isActive": True
    # },
    {
        "name": "Conexão Política",
        "sourceType": "rss",
        "rssUrl": "https://www.conexaopolitica.com.br/feed/",
        "credibilityLevel": "low",
        "isActive": True
    },
    {
        "name": "DCM",
        "sourceType": "rss",
        "rssUrl": "https://www.diariodocentrodomundo.com.br/feed/",
        "credibilityLevel": "low",
        "isActive": True
    },

    # HTML Sources (16th source - HTML scraping with BeautifulSoup)
    {
        "name": "Brasil Paralelo",
        "sourceType": "html",
        "htmlUrl": "https://www.brasilparalelo.com.br/noticias",
        "credibilityLevel": "low",
        "isActive": True,
        "htmlConfig": {
            "listingUrl": "https://www.brasilparalelo.com.br/noticias",
            "articleSelector": "._00-hobbit",
            "selectors": {
                "title": "h3._00-hobbit-title",
                "url": "a",
                "excerpt": "h3._00-hobbit-title"
            },
            "urlPrefix": "https://www.brasilparalelo.com.br",
            # Two-step scraping: follow links to extract full articles
            "followLinks": True,
            "maxArticles": 20,  # Limit to prevent API timeout
            "articlePage": {
                "contentSelector": ".w-richtext",
                "maxChars": 2000
            }
        }
    }
]


async def seed_sources():
    """Seed initial RSS and HTML sources into the database"""

    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.database_name]

    print(f"Connected to MongoDB: {settings.database_name}")
    print(f"Seeding {len(SOURCES)} sources (RSS + HTML)...\n")

    inserted_count = 0
    skipped_count = 0

    for source_data in SOURCES:
        # Check if source already exists (check by name for HTML sources)
        if 'rssUrl' in source_data:
            existing = await db.source_configuration.find_one({
                'rssUrl': source_data['rssUrl']
            })
        else:
            existing = await db.source_configuration.find_one({
                'name': source_data['name']
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
