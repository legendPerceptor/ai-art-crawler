# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Art Crawler is a Python application that fetches AI-generated artwork, prompts, and metadata from various AI art community platforms. It currently supports Civitai via API (no browser required) and can export data to the aicreatorvault platform.

**Architecture:**
- Async Python using `httpx` for HTTP requests
- Pydantic models for data validation and serialization
- SQLAlchemy for optional PostgreSQL storage
- Docker-based deployment
- Modular crawler design with base classes for extensibility

## Common Commands

### Docker (Primary deployment method)

```bash
# Build the Docker image
docker build -t ai-art-crawler -f docker/Dockerfile .

# Run crawler to fetch data (with aigc-xray proxy for external access)
docker run --rm \
  --network aicreatorvault_aicreatorvault-net \
  -e HTTP_PROXY=http://aigc-xray:1087 \
  -e HTTPS_PROXY=http://aigc-xray:1087 \
  -v $(pwd)/data:/data \
  ai-art-crawler \
  python scripts/run_crawler.py --site civitai --limit 50 --tag portrait --download

# Export fetched data to aicreatorvault (aigc-xray proxy is default in export script)
docker run --rm \
  --network aicreatorvault_aicreatorvault-net \
  -v $(pwd)/data:/data \
  ai-art-crawler \
  python scripts/export_to_aicv.py /data/crawled/civitai_*.json \
  --url http://aicreatorvault-backend-1:3001
```

### Local Development

```bash
# Install dependencies (using uv in the project's venv)
.venv/bin/pip install -e .

# Run crawler locally
python scripts/run_crawler.py --site civitai --limit 10 --tag portrait

# Run with database saving
DATABASE_URL="postgresql://user:pass@host:5432/db" \
  python scripts/run_crawler.py --site civitai --limit 10 --save-db

# Export to aicreatorvault
python scripts/export_to_aicv.py /data/crawled/civitai_*.json --url http://localhost:3001
```

### Linting and Code Quality

```bash
# Run ruff linter (configured in pyproject.toml, line-length: 100)
ruff check .

# Auto-fix linting issues
ruff check --fix .
```

## Architecture

### Data Model

All crawlers output the `Artwork` Pydantic model (defined in `crawler/base.py` and `crawler/civitai.py`):

```python
class Artwork(BaseModel):
    id: str                      # MD5 hash of source:source_id
    source: str                  # Platform name (e.g., "civitai")
    source_id: str               # Original ID on platform
    source_url: str              # Original URL
    prompt: str                  # Positive prompt
    negative_prompt: str         # Negative prompt
    model: str                   # AI model used
    style: str                   # Art style
    width/height: int            # Image dimensions
    image_url: str               # URL to image
    local_path: str              # Local file path if downloaded
    seed: Optional[int]          # Generation seed
    author: str                  # Creator username
    likes: int                   # Like count
    tags: list[str]              # Platform tags
    created_at: Optional[datetime]
    crawled_at: datetime
    raw_data: dict               # Original API response
```

### Crawler Architecture

**Base Crawler** (`crawler/base.py`):
- Abstract base class using Playwright for browser-based crawling
- Handles rate limiting, image downloading, and data persistence
- All crawlers inherit from `BaseCrawler` and implement `crawl()` method

**Civitai Crawler** (`crawler/civitai.py`):
- API-based crawler (no browser needed)
- Uses Civitai's public API at `https://civitai.com/api/v1`
- Supports cursor-based pagination and tag filtering
- Rate limited to 2 requests/second by default

### Storage Layer

**JSON Output** (default):
- Automatically saved to `{output_dir}/{site}_{timestamp}.json`
- DateTime fields are serialized to ISO format

**PostgreSQL** (optional):
- `storage/database.py` defines `ArtworkDB` SQLAlchemy model
- Uses `session.merge()` for idempotent inserts (prevents duplicates)
- Indexed on `source`, `source_id`, and `crawled_at`

### Export to aicreatorvault

**`scripts/export_to_aicv.py`**:
- Creates prompts via aicreatorvault API
- Uploads images (prefers local files, falls back to URL download)
- Associates images with prompts automatically
- Uses `aigc-xray` container proxy (`http://aigc-xray:1087`) by default for external downloads
- Set `autoAnalyze=false` for batch uploads (analyze separately)
- **Requires authentication** - must use `--email/--password` to login (auto-register) or `--user-id` directly

**Authentication (Required since aicreatorvault v2 multi-user update):**
```bash
# Login with email/password (auto-registers if user doesn't exist)
docker run --rm \
  --network aicreatorvault_aicreatorvault-net \
  -v $(pwd)/data:/data \
  ai-art-crawler \
  python scripts/export_to_aicv.py /data/crawled/civitai_*.json \
  --url http://aicreatorvault-backend-1:3001 \
  --email your@email.com --password yourpassword

# Or specify user ID directly (for existing users)
python scripts/export_to_aicv.py /data/crawled/civitai_*.json \
  --url http://localhost:3001 \
  --user-id 1
```

## Key Patterns

### Adding a New Crawler

1. Create a new crawler class inheriting from `BaseCrawler` (for browser-based) or implement API-based pattern like `CivitaiCrawler`
2. Implement the `crawl()` method returning `list[Artwork]`
3. Register in `scripts/run_crawler.py` `CRAWLERS` dict
4. Follow the rate limiting pattern using `self.rate_limit_wait()`

### Rate Limiting

All crawlers should respect rate limits:
```python
await self.rate_limit_wait()  # Wait before each request
```

### Async/Await Pattern

The codebase is fully async. Use:
```python
async with httpx.AsyncClient() as client:
    response = await client.get(url)
```

### Data Serialization

Pydantic models handle datetime serialization in `save_artworks()`:
```python
if isinstance(item.get('crawled_at'), datetime):
    item['crawled_at'] = item['crawled_at'].isoformat()
```

## Development Notes

- **Proxy Configuration**: Use the `aigc-xray` container for proxy access. Set `HTTP_PROXY=http://aigc-xray:1087` and `HTTPS_PROXY=http://aigc-xray:1087` environment variables. The export script defaults to this proxy.
- **Docker Networks**: The crawler should run on `aicreatorvault_aicreatorvault-net` to access both the aicreatorvault backend and the aigc-xray proxy container.
- **Output Directory**: Default is `data/crawled/` with images in `data/crawled/images/`
- **Rate Limits**: Civitai API is rate-limited to 2 req/sec by default. Adjust `rate_limit` parameter as needed.
- **Database**: PostgreSQL support is optional. Set `DATABASE_URL` environment variable to enable.

## File Structure

```
crawler/
  base.py          # Abstract BaseCrawler with Playwright
  civitai.py       # Civitai API implementation
scripts/
  run_crawler.py   # CLI to run any registered crawler
  export_to_aicv.py # Export to aicreatorvault platform
storage/
  database.py      # SQLAlchemy models and operations
config/
  settings.py      # Pydantic Settings for configuration
data/
  crawled/         # JSON output files
  images/          # Downloaded images
```
