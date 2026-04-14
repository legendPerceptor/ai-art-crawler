# AI Art Crawler

[中文文档](README_zh.md)

Crawl prompts and images from AI art community websites, with support for importing into the aicreatorvault platform.

## 🎯 Supported Sites

| Site | Status | Features |
|------|--------|----------|
| **Civitai** | ✅ Implemented | API support, no browser required |
| **Lexica** | 🚧 Planned | Stable Diffusion image gallery |
| **PromptHero** | 🚧 Planned | Prompt search engine |

## 🚀 Quick Start

### Option 1: Local Run (Recommended for Development)

**Install dependencies**:

```bash
# Install with uv (recommended)
uv sync
# Editable Install
uv pip install -e .
```

**Run the crawler**:

```bash
# Basic usage
uv run python scripts/run_crawler.py --site civitai --limit 50 --download

# With proxy
HTTPS_PROXY=http://localhost:1087 python scripts/run_crawler.py --limit 100 --download

# Get this week's most popular images
uv run python scripts/run_crawler.py --limit 50 --period Week --sort "Most Reactions" --download

# Save to database
DATABASE_URL="postgresql://user:pass@localhost:5432/db" \
  python scripts/run_crawler.py --limit 50 --save-db
```

**Export to aicreatorvault**:

```bash
# Import data (authentication required - login with email, auto-register if user doesn't exist)
uv run python scripts/export_to_aicv.py data/crawled/civitai_*.json \
  --url http://localhost:3001 \
  --email your@email.com --password yourpassword

# Or specify user ID directly
uv run python scripts/export_to_aicv.py data/crawled/civitai_*.json \
  --url http://localhost:3001 --user-id 1

# Use legacy API (disable knowledge graph)
uv run python scripts/export_to_aicv.py data/crawled/civitai_*.json --url http://localhost:3001 --no-kg

# Limit import count (for testing)
uv run python scripts/export_to_aicv.py data/crawled/civitai_*.json --limit 10
```

---

### Option 2: Docker Compose (Recommended for Deployment)

**Build the image**:

```bash
docker build -t ai-art-crawler -f docker/Dockerfile .
```

**Crawl data**:

```bash
# Using docker compose
docker compose --profile crawl run --rm crawler
```


```bash
# Crawl 50 portrait images (proxy configuration required)
docker run --rm \
  --network aicreatorvault-net \
  -e HTTP_PROXY=http://aigc-xray:1087 \
  -e HTTPS_PROXY=http://aigc-xray:1087 \
  -v $(pwd)/data:/data \
  ai-art-crawler \
  python scripts/run_crawler.py --site civitai --limit 50 --tag portrait --download
```

**Import to aicreatorvault** (authentication required):

```bash
docker run --rm \
  --network aicreatorvault-net \
  -v $(pwd)/data:/data \
  ai-art-crawler \
  python scripts/export_to_aicv.py /data/crawled/civitai_*.json \
  --url http://aicreatorvault-backend-1:3001 \
  --email your@email.com --password yourpassword
```

### CLI Arguments

**Crawler arguments**:
- `--site civitai` - Crawl from Civitai
- `--limit 50` - Number of items to crawl
- `--download` - Download images to local storage
- `--save-db` - Save to database (requires DATABASE_URL)
- `--period Day` - Time period: AllTime, Year, Month, Week, Day
- `--sort Newest` - Sort order: Newest, Most Reactions, Most Comments

**Fetching different data**:
```bash
# Today's newest
python scripts/run_crawler.py --limit 50 --period Day --sort Newest

# This week's most popular
python scripts/run_crawler.py --limit 50 --period Week --sort "Most Reactions"

# All-time most popular
python scripts/run_crawler.py --limit 50 --period AllTime --sort "Most Reactions"
```

**Export arguments**:
- `--url` - aicreatorvault backend URL
- `--limit 10` - Limit import count (optional)
- `--no-kg` - Disable knowledge graph mode (use legacy API)
- `--no-download` - Don't upload images (import prompts only)
- `--proxy` - Proxy server (optional)
- `--no-proxy` - Don't use proxy (optional)

## 📁 Data Format

Crawled data is saved in JSON format:

```json
{
  "source": "civitai",
  "source_id": "12097475",
  "prompt": "score_9, score_8_up, score_7_up, 1girl, full body...",
  "negative_prompt": "score_6, score_5, score_4",
  "image_url": "https://image.civitai.com/...",
  "local_path": "/data/crawled/images/xxx.jpeg",
  "width": 1520,
  "height": 1952,
  "seed": 3269595310,
  "author": "Stellaaa",
  "likes": 0
}
```

## 🛠️ Complete Examples

### Scenario 1: Crawl and import 100 portrait images (Docker Compose)

```bash
# Step 1: Crawl data
docker compose --profile crawl run --rm crawler \
  python scripts/run_crawler.py --site civitai --limit 100 --tag portrait --download

# Step 2: Import to aicreatorvault
docker compose --profile export run --rm exporter
```

### Scenario 2: Test mode - Crawl 10 items

```bash
# Crawl prompts only, without downloading images
docker compose --profile crawl run --rm crawler \
  python scripts/run_crawler.py --site civitai --limit 10 --tag portrait

# Import first 5 items for testing
docker compose --profile export run --rm exporter \
  python scripts/export_to_aicv.py /data/crawled/civitai_*.json --url $$AICV_URL --limit 5
```

## 📊 Project Structure

```
ai-art-crawler/
├── crawler/
│   ├── base.py           # Base crawler class
│   └── civitai.py        # Civitai API crawler
├── scripts/
│   ├── run_crawler.py    # Run crawler
│   └── export_to_aicv.py # Export to aicreatorvault
├── storage/
│   └── database.py       # Database operations
├── config/
│   └── settings.py       # Configuration
├── docker/
│   └── Dockerfile        # Docker image
├── data/                 # Data directory
│   ├── crawled/          # Crawled JSON files
│   └── images/           # Downloaded images
├── docker-compose.yml    # Docker Compose configuration
├── requirements.txt
└── README.md
```

## 🔧 Advanced Configuration

### Using a Proxy

The crawler requires a proxy to access external websites. Docker Compose mode is pre-configured with the `aigc-xray` proxy:

```bash
# Docker Compose mode (auto-configured)
HTTP_PROXY=http://aigc-xray:1087
HTTPS_PROXY=http://aigc-xray:1087

# docker run mode requires manual specification
docker run --rm \
  --network aicreatorvault-net \
  -e HTTP_PROXY=http://aigc-xray:1087 \
  -e HTTPS_PROXY=http://aigc-xray:1087 \
  ...
```

### Saving to Database

```bash
# Docker Compose mode (DATABASE_URL pre-configured)
docker compose --profile crawl run --rm crawler \
  python scripts/run_crawler.py --site civitai --limit 50 --save-db

# docker run mode requires manual specification
docker run --rm \
  --network aicreatorvault-net \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  ai-art-crawler \
  python scripts/run_crawler.py --site civitai --limit 50 --save-db
```

## ⚠️ Notices

1. **Respect robots.txt** - Follow the website's crawler protocol
2. **Rate limiting** - Default 2 requests/second to avoid overwhelming the target site
3. **Data usage** - For personal testing only, not for commercial use
4. **Copyright** - Be mindful of image copyright and licensing

## 🔄 aicreatorvault Integration

### Knowledge Graph Mode (Default)

Import flow:

1. **Create prompt asset** - Create a Prompt asset via `/api/assets`
2. **Upload image asset** - Create an Image asset via `/api/assets/upload`
3. **Create graph relationship** - Create a Prompt → Image `generated` relationship via `/api/relationships`

After importing, you can view in the aicreatorvault frontend's "Knowledge Graph" page:
- Asset nodes (prompts, images)
- Relationship edges (generated relationships)
- Graph visualization

### Legacy API Mode

Use the `--no-kg` flag to enable the legacy API:

1. **Create prompt** - Create a prompt via `/api/prompts`
2. **Upload image** - Upload an image via `/api/images` and associate with promptId
3. **Associate data** - Images are automatically associated with the prompt

### API Comparison

| Feature | Knowledge Graph Mode (Default) | Legacy API Mode (--no-kg) |
|---------|-------------------------------|--------------------------|
| Prompt creation | `/api/assets` (type: prompt) | `/api/prompts` |
| Image upload | `/api/assets/upload` | `/api/images` |
| Relationship management | `/api/relationships` | Auto-associated via promptId |
| Graph support | ✅ Full knowledge graph | ❌ Basic association only |
| Rating range | 0-10 | 0-5 |
| Frontend display | "Knowledge Graph" tab | "Prompts" and "Images" tabs |

## 📝 Roadmap

- [x] Civitai API crawler
- [x] Image download
- [x] aicreatorvault import
- [x] Deduplication (multi-file import and cross-file deduplication)
- [x] Knowledge graph support (Prompt -> Image relationships)
- [ ] Lexica crawler
- [ ] PromptHero crawler
- [ ] Midjourney crawler
- [ ] Scheduled tasks

## 📄 License

MIT
