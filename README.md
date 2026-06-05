# ZenianResearchBot

Semantic research paper discovery via Telegram, backed by a vector index of 15,000+ Springer Link articles. A scraper pipeline ingests and summarizes papers with Ollama, embeds them with MiniLM, and stores them in Pinecone. The Telegram bot answers natural-language queries and sends weekly research highlights.

## Features

- **Semantic search** — Ask about a research topic; the bot returns the best-matching paper from the vector index.
- **Weekly research sparks** — Subscribed users receive a curated paper every 7 days (6 PM IST).
- **YouTube enrichment** — Gemini extracts keywords; the bot attaches related YouTube videos.
- **Resumable ingestion** — The scraper checkpoints progress and tracks per-stage failure stats.
- **Health monitoring** — Periodic Pinecone connectivity checks for deployed bot instances.

## Architecture

```
Springer Link  -->  Playwright Scraper  -->  Ollama (summarize)
                                                    |
                                                    v
Telegram User  -->  Embed Query  -->  Pinecone  <--  MiniLM Embeddings
                         |                |
                         v                v
                    Gemini + YouTube   Metadata (title, summary, link)
```

| Component | Directory | Purpose |
|-----------|-----------|---------|
| Scraper pipeline | `scraper/` | Scrape, summarize, embed, and upsert articles |
| Telegram bot | `Bot/` | Query interface and scheduled digests |
| Container | `Dockerfile` | Bot deployment (e.g. Hugging Face Spaces) |

Both components share the same Pinecone index and embedding model (`all-MiniLM-L6-v2`, 384 dimensions).

## Pipeline Results

From a full ingestion run (August 2025):

| Metric | Value |
|--------|-------|
| Articles processed | 15,557 |
| Successful | 15,145 |
| Failed | 412 |
| Success rate | 97.4% |

Failure breakdown: scraping (165), summarization (165), embedding (24), Pinecone (0).

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com/) (for the scraper summarization step)
- [Pinecone](https://www.pinecone.io/) account and index (384-dim, cosine metric)
- Telegram Bot Token ([@BotFather](https://t.me/BotFather))
- Google Gemini API key
- YouTube Data API v3 key

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/RohitDSonawane/ZenianResearchBot.git
cd ZenianResearchBot
```

Copy the example env files and fill in your credentials:

```bash
cp scraper/.env.example scraper/.env
cp Bot/.env.example Bot/.env
```

**Important:** `PINECONE_INDEX_NAME` must match in both `scraper/.env` and `Bot/.env`.

### 2. Run the scraper (ingestion)

```bash
cd scraper
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

# Ensure Ollama is running and the configured model is pulled
ollama pull gemma3:1b

python main.py
```

The scraper writes logs and checkpoints to `scraper/logs/` (gitignored). Interrupt safely with `Ctrl+C`; progress resumes from the last checkpoint.

### 3. Run the Telegram bot (local)

```bash
cd Bot
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python query_bot.py
```

Send `/start` in Telegram, then message a research topic.

## Environment Variables

### Bot (`Bot/.env`)

| Variable | Description |
|----------|-------------|
| `TELEGRAM_TOKEN` | Telegram bot token |
| `GEMINI_API_KEY` | Google Gemini API key |
| `YOUTUBE_API_KEY` | YouTube Data API v3 key |
| `PINECONE_API_KEY` | Pinecone API key |
| `PINECONE_INDEX_NAME` | Pinecone index name (default: `research-abstracts`) |

### Scraper (`scraper/.env`)

See `scraper/.env.example` for the full list. Required variables:

| Variable | Description |
|----------|-------------|
| `PINECONE_API_KEY` | Pinecone API key |
| `PINECONE_INDEX_NAME` | Index name (must match bot) |
| `OLLAMA_HOST` / `OLLAMA_PORT` | Ollama server address |
| `OLLAMA_MODEL` | Model used for summarization |

## Deploying the Bot (Docker / Hugging Face Spaces)

The included `Dockerfile` builds and runs the Telegram bot:

```bash
docker build -t zenian-research-bot .
docker run --env-file Bot/.env zenian-research-bot
```

For [Hugging Face Spaces](https://huggingface.co/spaces), create a Docker Space and add the bot secrets (`TELEGRAM_TOKEN`, `GEMINI_API_KEY`, `YOUTUBE_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`) as Space secrets. The bot uses polling and includes periodic health checks suitable for long-running Space deployments.

The scraper is intended to run locally (requires Playwright + Ollama) and is not included in the Docker image.

## Project Structure

```
ZenianResearchBot/
├── Bot/
│   ├── query_bot.py          # Telegram bot entry point
│   ├── embedding_service.py  # Sentence-transformer embeddings
│   ├── pinecone_client.py    # Pinecone query client
│   ├── requirements.txt
│   └── .env.example
├── scraper/
│   ├── main.py               # Ingestion pipeline entry point
│   ├── config.py             # Configuration and validation
│   ├── src/
│   │   ├── scraper.py        # Playwright article scraper
│   │   ├── ollama_service.py # Summarization via Ollama
│   │   ├── pinecone_client.py
│   │   ├── embedding_service.py
│   │   └── utils.py
│   ├── requirements.txt
│   └── .env.example
├── Dockerfile
├── LICENSE
└── .github/workflows/ci.yml
```

## Limitations and Ethics

- The scraper targets Springer Link search results. Respect the site's terms of service and rate limits; adjust `CONCURRENCY_LIMIT` and wait settings accordingly.
- Embedding and search quality depend on Ollama summary quality and the `all-MiniLM-L6-v2` model.
- The weekly spark uses in-memory chat ID tracking; restarting the bot clears subscriptions until users message again.

## Security

Never commit `.env` files or API keys. If a key was previously exposed in git history, rotate it in the provider dashboard and consider rewriting git history before publishing.

## License

MIT — see [LICENSE](LICENSE).
