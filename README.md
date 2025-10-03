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

Create client in Ory Hydra:

```bash
ory create oauth2-client \
  --endpoint http://localhost:4445 \
  --name "Monitoring POC" \
  --grant-type client_credentials \
  --scope "openid offline_access" \
  --token-endpoint-auth-method client_secret_basic
```

Update `.env` with generated credentials.

### 3. Access

Dashboard: http://localhost:8000

## Architecture

### Data Flow

```
RSS Feeds → RSSExtractor → PreFilter (scoring) → MongoDB
                                                      ↓
                                          (score ≥ 30 & status=pending)
                                                      ↓
                                          SubmissionService → OAuth2 → AletheiaFact API
```

### Pre-Filter Scoring (60 points total)

**Content Quality (20 pts)**
- Length ≥ 150 chars: 10 pts
- Contains 2+ sentences: 10 pts

**Fact-Checkable Indicators (30 pts)**
- Numbers/percentages: 10 pts
- Factual keywords (confirmou, anunciou, estudo, pesquisa): 10 pts
- Domain keywords (governo, vacina, cientista): 10 pts

**Source Risk Priority (10 pts)**
- Low credibility: 10 pts (HIGHEST PRIORITY - likely misinformation)
- Medium credibility: 5 pts
- High credibility: 3 pts

**Submission Threshold**: 30 points

### RSS Sources (10 Brazilian news sites)

**High Credibility**: G1, Folha, O Globo, Estadão, UOL, BBC Brasil, CNN Brasil

**Medium Credibility**: R7, CartaCapital, Poder360

## Configuration

Required environment variables:

```bash
# AletheiaFact API
ALETHEIA_BASE_URL=http://localhost:3000

# Ory Hydra OAuth2
ORY_HYDRA_ADMIN_URL=http://localhost:4445
ORY_HYDRA_PUBLIC_URL=http://localhost:4444
ORY_CLIENT_ID=your_client_id
ORY_CLIENT_SECRET=your_secret
ORY_SCOPE=openid offline_access

# Optional
RECAPTCHA_TOKEN=
EXTRACTION_INTERVAL_MINUTES=30
SUBMISSION_SCORE_THRESHOLD=30
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

**Stats & Integration**
- GET /api/stats
- GET /api/aletheia/status
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

## Status States

- **pending**: Awaiting submission (score ≥ 30)
- **submitted**: Successfully sent to AletheiaFact
- **rejected**: Below score threshold
- **failed**: Submission error (retryable)

## Troubleshooting

**No extractions**: Check scheduler logs, verify sources are active, manually trigger extraction

**Submission failures**: Check `/api/aletheia/status`, review OAuth2 config, inspect failed content errors

**Low submission rate**: Review pre-filter scores in `/api/stats`, verify credibility levels

**Duplicates**: System auto-deduplicates via SHA-256 hash of URL + content

## Success Metrics

- 100+ articles extracted daily
- 20+ verification requests submitted daily
- 90%+ submission success rate
- Stable OAuth2 authentication
- Continuous operation for 1+ week

## License

Proof-of-concept project for AletheiaFact integration.
