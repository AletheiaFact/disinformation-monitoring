# Disinformation Monitoring POC

A proof-of-concept system for automated extraction, filtering, and submission of Brazilian news content to AletheiaFact for fact-checking verification.

## Overview

This system:
- Extracts content from 10 Brazilian news RSS feeds every 30 minutes
- Applies intelligent pre-filtering with scoring that prioritizes potential misinformation sources
- Automatically submits qualifying content to AletheiaFact via OAuth2
- Provides a dashboard for monitoring extraction and submission statistics
- Handles deduplication to prevent duplicate submissions

## Technical Stack

- **Backend**: Python 3.11+, FastAPI (async)
- **Database**: MongoDB with Motor (async driver)
- **Scheduling**: APScheduler (periodic extraction)
- **Container**: Docker & Docker Compose
- **Libraries**: feedparser, BeautifulSoup4, langdetect, httpx

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- AletheiaFact OAuth2 credentials (client ID and secret)

### 1. Clone and Setup

```bash
cd poc-disinformation-monitoring
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file with your Ory Hydra OAuth2 credentials:

```bash
# AletheiaFact API
ALETHEIA_BASE_URL=http://localhost:3000

# Ory Hydra OAuth2 (Client Credentials Flow)
ORY_HYDRA_ADMIN_URL=http://localhost:4445
ORY_HYDRA_PUBLIC_URL=http://localhost:4444
ORY_CLIENT_ID=your_client_id_here
ORY_CLIENT_SECRET=your_client_secret_here
ORY_SCOPE=openid offline_access

# Recaptcha (optional - leave empty to skip validation in dev)
RECAPTCHA_TOKEN=
```

> **Note**: See [OAUTH2_CLIENT_CREDENTIALS.md](./OAUTH2_CLIENT_CREDENTIALS.md) for detailed OAuth2 setup instructions.

### 3. Start the System

```bash
docker-compose up -d
```

This will:
- Start MongoDB on port 27017
- Start the FastAPI application on port 8000
- Begin scheduled extraction every 30 minutes

### 4. Seed Initial Sources

```bash
docker-compose exec api python scripts/seed_sources.py
```

This populates the database with 10 Brazilian news sources.

### 5. Access Dashboard

Open your browser to: `http://localhost:8000`

### 6. Create OAuth2 Client in Ory Hydra

Before the system can submit content, create an OAuth2 client:

```bash
# Using Ory CLI
ory create oauth2-client \
  --endpoint http://localhost:4445 \
  --name "Monitoring POC" \
  --grant-type client_credentials \
  --scope "openid offline_access" \
  --token-endpoint-auth-method client_secret_basic

# Copy the client_id and client_secret to your .env file
```

Or see [OAUTH2_CLIENT_CREDENTIALS.md](./OAUTH2_CLIENT_CREDENTIALS.md) for other methods.

### 7. Verify Connection

The dashboard will show both API and OAuth2 connection status. The system will automatically submit qualifying content every 30 minutes.

## System Architecture

### Pre-Filter Scoring Logic

Content is scored from 0-60 points across three categories:

#### 1. Content Quality (20 points)
- Length ≥ 150 characters: 10 points
- Contains 2+ complete sentences: 10 points

#### 2. Fact-Checkable Indicators (30 points)
- Contains numbers/percentages: 10 points
- Contains factual keywords: 10 points
  - Portuguese: "confirmou", "anunciou", "estudo", "pesquisa", "dados", etc.
- Contains domain keywords: 10 points
  - Political: "governo", "presidente", "ministro", "eleição"
  - Health: "vacina", "covid", "saúde", "hospital"
  - Science: "cientista", "universidade", "pesquisa"

#### 3. Source Risk Priority (10 points)
**CRITICAL**: Low credibility sources receive HIGHEST priority
- **Low credibility: 10 points** (HIGH PRIORITY - likely misinformation)
- Medium credibility: 5 points
- High credibility: 3 points (still monitored but lower urgency)

**Submission Threshold**: Score ≥ 30 points

This scoring system prioritizes content from less credible sources that contains factual claims, making it ideal for proactive misinformation monitoring.

### RSS Sources

10 Brazilian news sources with credibility classification:

**High Credibility:**
- G1, Folha de S.Paulo, O Globo, Estadão, UOL, BBC Brasil, CNN Brasil

**Medium Credibility:**
- R7, CartaCapital, Poder360

## API Endpoints

### Source Management

```
GET    /api/sources              # List all sources
POST   /api/sources              # Add new RSS source
PUT    /api/sources/{id}         # Update source
DELETE /api/sources/{id}         # Delete source
POST   /api/sources/{id}/extract # Manually trigger extraction
```

### Content Management

```
GET    /api/content              # List content (with filters)
GET    /api/content/{id}         # Get single content item
POST   /api/content/{id}/submit  # Retry submission
DELETE /api/content/{id}         # Delete content
```

### Statistics

```
GET    /api/stats                # Dashboard statistics
```

### AletheiaFact Integration

```
GET    /api/aletheia/status      # Check API connection status
POST   /api/aletheia/submit-pending  # Submit all pending
```

## Dashboard Features

### API Status Section
- API connection status indicator
- "Submit Pending Items" button for manual batch submission

### Statistics Cards
- Total extracted today
- Total submitted (all time)
- Submission success rate
- Average pre-filter score

### Content Status Breakdown
- Pending: Awaiting submission
- Submitted: Successfully sent to AletheiaFact
- Rejected: Below score threshold
- Failed: Submission error (can retry)

### Content Table
- View all extracted content
- Filter by status
- Sort by date or score
- Click to view full details
- Retry failed submissions

### Sources Status
- List of all sources
- Active/inactive indicator
- Last extraction time
- Extraction and submission counts

## Configuration

### Environment Variables

```bash
# MongoDB
MONGODB_URL=mongodb://mongodb:27017
DATABASE_NAME=monitoring_poc

# Logging
LOG_LEVEL=info

# AletheiaFact API
ALETHEIA_BASE_URL=http://localhost:3000

# Recaptcha (optional - leave empty to skip validation in dev)
RECAPTCHA_TOKEN=

# Scheduler (optional - defaults shown)
EXTRACTION_INTERVAL_MINUTES=30

# Submission (optional - defaults shown)
SUBMISSION_SCORE_THRESHOLD=30
MAX_BATCH_SUBMISSION=100
```

### MongoDB Indexes

Automatically created on startup:

**ExtractedContent:**
- `contentHash` (unique)
- `status` + `extractedAt` (compound)
- `preFilterScore` (descending)

**SourceConfiguration:**
- `isActive`
- `lastExtraction`
- `rssUrl` (unique)

## OAuth2 Configuration

This system uses **OAuth2 Client Credentials flow** via Ory Hydra for machine-to-machine authentication.

### How It Works

1. **Token Generation**: System requests access token from Ory Hydra using client credentials
2. **Token Caching**: Token cached in memory for ~59 minutes (auto-refreshes 60s before expiry)
3. **API Calls**: Access token included in `Authorization: Bearer <token>` header
4. **Auto-Refresh**: Transparent token refresh when expired

### Configuration

```bash
# AletheiaFact API endpoint
ALETHEIA_BASE_URL=http://localhost:3000

# Ory Hydra endpoints
ORY_HYDRA_ADMIN_URL=http://localhost:4445  # Admin API
ORY_HYDRA_PUBLIC_URL=http://localhost:4444  # Token endpoint

# OAuth2 client credentials
ORY_CLIENT_ID=monitoring-poc-client
ORY_CLIENT_SECRET=your_secret_here
ORY_SCOPE=openid offline_access
```

### Creating OAuth2 Client

See [OAUTH2_CLIENT_CREDENTIALS.md](./OAUTH2_CLIENT_CREDENTIALS.md) for detailed instructions on:
- Creating OAuth2 clients in Ory Hydra
- Testing token generation
- Troubleshooting authentication issues

## Verification Request Mapping

Content is mapped to AletheiaFact's CreateVerificationRequestDTO:

```json
{
  "content": "Article main text...",
  "receptionChannel": "automated_monitoring",
  "reportType": "claim",
  "impactArea": {"label": "Politics", "value": "politics"},
  "source": [{"href": "https://source-url.com/article"}],
  "publicationDate": "2025-01-15T10:30:00",
  "date": "2025-01-15T11:00:00",
  "heardFrom": "Automated Monitoring - G1",
  "recaptcha": "optional_token_for_captcha_validation"
}
```

**Note**: The `recaptcha` field is optional in development. Set `RECAPTCHA_TOKEN` in `.env` if your AletheiaFact instance requires it.

### Impact Area Detection

Automatic keyword-based classification:
- **Politics**: governo, presidente, ministro, eleição
- **Health**: vacina, covid, saúde, hospital
- **Science**: cientista, pesquisa, estudo, universidade
- **General**: Default fallback

## Manual Intervention Workflows

### Add New RSS Source

```bash
curl -X POST http://localhost:8000/api/sources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Source",
    "rssUrl": "https://newssite.com/rss",
    "credibilityLevel": "medium",
    "isActive": true
  }'
```

### Manually Trigger Extraction

```bash
curl -X POST http://localhost:8000/api/sources/{source_id}/extract
```

### Retry Failed Submission

Use the "Retry" button in the dashboard, or:

```bash
curl -X POST http://localhost:8000/api/content/{content_id}/submit
```

### Submit All Pending

Use the "Submit Pending Items" button in the dashboard, or:

```bash
curl -X POST http://localhost:8000/api/aletheia/submit-pending?limit=100
```

## Monitoring and Logs

### View Application Logs

```bash
docker-compose logs -f api
```

### View Scheduler Activity

Logs show:
- Extraction start/completion
- Number of articles extracted per source
- Submission attempts and results
- Token refresh activities

### MongoDB Direct Access

```bash
docker-compose exec mongodb mongosh monitoring_poc
```

Useful queries:

```javascript
// Count by status
db.extracted_content.countDocuments({status: "pending"})

// Top sources by extraction count
db.source_configuration.find().sort({totalExtracted: -1})

// Recent submissions
db.extracted_content.find({status: "submitted"}).sort({submittedToAletheiaAt: -1}).limit(10)

// Failed submissions with errors
db.extracted_content.find({status: "failed"}, {title: 1, submissionError: 1})
```

## Troubleshooting

### API Connection Issues

**Problem**: Unable to submit verification requests

**Solution**:
1. Check API status: `GET /api/aletheia/status`
2. Verify `.env` has correct `ALETHEIA_BASE_URL`
3. Ensure AletheiaFact instance is running on specified port
4. Check logs for API error details

### Extraction Not Running

**Problem**: No new content being extracted

**Solution**:
1. Check scheduler logs: `docker-compose logs api | grep scheduler`
2. Verify sources are active: `GET /api/sources`
3. Manually trigger extraction for one source to test
4. Check RSS feed accessibility (firewall/network issues)

### Submissions Failing

**Problem**: Content stuck in "failed" status

**Solution**:
1. Check submission errors in content details
2. Common issues:
   - 401: OAuth token expired (re-authenticate)
   - 400: Validation error (check VR payload)
   - 500: AletheiaFact API unavailable (retry later)
3. Use "Retry" button after resolving issue

### Duplicate Content

**Problem**: Same article appearing multiple times

**Solution**:
- System automatically deduplicates using SHA-256 hash of URL + content
- Check database for duplicate `contentHash` values
- May indicate RSS feed republishing old articles

### Low Submission Rate

**Problem**: Few items being submitted despite many extractions

**Solution**:
1. Check pre-filter score distribution: `GET /api/stats`
2. Verify scoring threshold (default: 30)
3. Review source credibility levels
4. Check language detection (only Portuguese content submitted)

## Production Deployment Considerations

For production deployment, consider:

1. **Security**:
   - Use environment-specific `.env` files
   - Store secrets in secure vault (not `.env`)
   - Enable HTTPS/TLS
   - Restrict CORS origins
   - Add authentication to API endpoints

2. **Scalability**:
   - Use managed MongoDB service
   - Implement rate limiting
   - Add request queuing for submissions
   - Scale horizontally with load balancer

3. **Reliability**:
   - Add health checks and monitoring
   - Implement retry strategies with exponential backoff
   - Set up alerting for failures
   - Enable log aggregation

4. **Performance**:
   - Add caching layer (Redis)
   - Optimize database queries
   - Implement pagination for large datasets
   - Use CDN for frontend assets

## Success Criteria

The POC is successful if:

- ✅ Extracts 100+ articles daily from 10 sources
- ✅ Pre-filter correctly prioritizes low-credibility sources
- ✅ Successfully submits 20+ VRs daily to AletheiaFact
- ✅ OAuth2 authentication remains stable
- ✅ VRs appear with "pre_triage" status in AletheiaFact
- ✅ System runs continuously for 1 week
- ✅ 90%+ submission success rate

## Development

### Running Locally (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Start MongoDB
mongod --dbpath ./data/db

# Run application
python -m uvicorn app.main:app --reload
```

### Running Tests

```bash
# TODO: Add test suite
pytest tests/
```

## License

This is a proof-of-concept project for AletheiaFact integration.

## Support

For issues or questions:
- Check the troubleshooting section above
- Review application logs
- Contact AletheiaFact team for API-related issues
