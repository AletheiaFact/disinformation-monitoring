# Disinformation Monitoring POC

Automated system for extracting Brazilian news content from RSS feeds, scoring with intelligent pre-filtering, and submitting to AletheiaFact for fact-checking verification via OAuth2.

## Tech Stack

- Python 3.11+, FastAPI (async)
- MongoDB with Motor (async driver)
- APScheduler for periodic extraction
- Docker & Docker Compose
- OAuth2 Client Credentials (Ory Hydra)

## Quick Start

### 1. Setup

```bash
cp .env.example .env
# Edit .env with your OAuth2 credentials
docker-compose up -d
docker-compose exec api python scripts/seed_sources.py
```

### 2. Configure OAuth2

Obtain M2M (machine-to-machine) OAuth2 credentials from AletheiaFact team and update `.env` with the provided client ID and secret.

### 3. Access

Dashboard: http://localhost:8000

## Architecture

### Multi-Source Extraction

The system uses a **Factory Pattern** for flexible content extraction:

- **ExtractorFactory**: Routes to appropriate extractor based on `sourceType`
- **RSSExtractor**: Parses RSS/Atom feeds via feedparser (15 sources)
- **HTMLExtractor**: Scrapes static HTML pages via BeautifulSoup (1 source)
- **Future**: API extractors for JSON/REST sources

### Data Flow

```
RSS Feeds ──┐
            ├→ ExtractorFactory → [RSSExtractor or HTMLExtractor] → PreFilter (scoring) → MongoDB
HTML Pages ─┘                                                                                  ↓
                                                                              (score ≥ 38 & status=pending)
                                                                                               ↓
                                                                   SubmissionService → OAuth2 → AletheiaFact API
```

### Pre-Filter Scoring (60 points total, threshold: 38)

**Tiered Base Scoring** (pick highest, not additive)
- Government entities: 12 pts
- Political keywords: 10 pts
- Domain keywords: 8 pts

**Verifiable Data** (10 pts each)
- Percentages, currency, numbers with context

**Checkability Signals**
- Direct quotes: +8 pts
- Attributions: +6 pts
- Named entities: +4 pts

**Source Risk Priority**
- Low credibility: 10 pts (HIGHEST PRIORITY - misinformation monitoring)
- Medium credibility: 5 pts
- High credibility: 3 pts

**Context-Aware Penalties**
- Speculation: -15 pts
- Conditional statements: -12 pts
- Vague language: -8 pts

**Bonuses**
- Official guidance: +6 pts
- Health/safety advisories: +8 pts

### Content Sources (16 total: 15 RSS + 1 HTML)

**High Credibility** (4 RSS): G1, Folha de S.Paulo, BBC Brasil, Estado de S.Paulo

**Medium Credibility** (6 RSS): CNN Brasil, Poder360, CartaCapital, Gazeta do Povo, Metrópoles, The Intercept Brasil

**Low Credibility** (5 RSS + 1 HTML): Terça Livre, Jornal da Cidade Online, Brasil 247, Conexão Política, DCM, Brasil Paralelo

## Configuration

Required environment variables:

```bash
# AletheiaFact API
ALETHEIA_BASE_URL=http://localhost:3000

# Ory Hydra OAuth2
ORY_CLIENT_ID=your_client_id
ORY_CLIENT_SECRET=your_secret
ORY_SCOPE=openid offline_access

# Optional
RECAPTCHA_TOKEN=
EXTRACTION_INTERVAL_MINUTES=30
MINIMUM_SAVE_SCORE=20
SUBMISSION_SCORE_THRESHOLD=38
AUTO_SUBMIT_ENABLED=false
MAX_BATCH_SUBMISSION=100
```

## API Endpoints

**Sources**
- GET /api/sources
- POST /api/sources
- PUT /api/sources/{id}
- DELETE /api/sources/{id}
- POST /api/sources/{id}/extract

**Content**
- GET /api/content
- GET /api/content/{id}
- POST /api/content/{id}/submit
- DELETE /api/content/{id}

**Integration**
- POST /api/aletheia/submit-pending

## Manual Operations

**Trigger extraction**:
```bash
curl -X POST http://localhost:8000/api/sources/{source_id}/extract
```

**Submit pending**:
```bash
curl -X POST http://localhost:8000/api/aletheia/submit-pending?limit=100
```

**View logs**:
```bash
docker-compose logs -f api
```

**MongoDB shell**:
```bash
docker-compose exec mongodb mongosh monitoring_poc
```

## Verification Request Mapping

Submitted to AletheiaFact as:

```json
{
  "content": "Article text...",
  "receptionChannel": "automated_monitoring",
  "reportType": "claim",
  "impactArea": {"label": "Politics", "value": "politics"},
  "source": [{"href": "https://source-url.com"}],
  "publicationDate": "2025-01-15T10:30:00",
  "date": "2025-01-15T11:00:00",
  "heardFrom": "Automated Monitoring - Source Name",
  "recaptcha": "optional_token"
}
```

Impact areas detected via keywords: Politics, Health, Science, General.

## Deduplication Strategy

**Two-layer efficient deduplication**:

1. **Early URL Check** (90% processing reduction)
   - Normalize URL (remove tracking params, upgrade http→https)
   - Check indexed `sourceUrl` before NLP processing
   - Skip duplicate entries immediately

2. **Content Hash Fallback**
   - SHA-256 hash of `url + normalized_content`
   - Catches same article on different URLs

**Performance**: RSS feeds fetched normally, but duplicate entries skip claim extraction, scoring, and language detection.

## Status States

- **pending**: Awaiting submission (score ≥ 38)
- **submitted**: Successfully sent to AletheiaFact
- **rejected**: Below score threshold
- **failed**: Submission error (retryable)

## Troubleshooting

**No extractions**: Check scheduler logs, verify sources are active, manually trigger extraction

**Submission failures**: Review OAuth2 config, inspect failed content errors in dashboard

**Low submission rate**: Review pre-filter scores in `/api/stats`, verify credibility levels

**Duplicates**: Automatically handled via URL normalization + indexed checks

## Success Metrics

- 100+ articles extracted daily
- 20+ verification requests submitted daily
- 90%+ submission success rate
- Stable OAuth2 authentication
- Continuous operation for 1+ week

## License

Proof-of-concept project for AletheiaFact integration.
