# ZenianResearchBot

A Telegram bot that finds research papers by meaning instead of keywords. It searches a vector index of more than 15,000 Springer Link articles. A scraper pipeline collects the papers, summarizes each one with Ollama, embeds the summary with MiniLM and stores it in Pinecone. The bot takes a question in plain language, returns the closest paper and sends subscribers a weekly highlight.

Status: no hosted instance is running right now. The code is complete, and the steps below deploy it.

[![CI](https://github.com/RohitDSonawane/ZenianResearchBot/actions/workflows/ci.yml/badge.svg)](https://github.com/RohitDSonawane/ZenianResearchBot/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Features

- Semantic search. Ask about a research topic and the bot returns the best-matching paper from the index.
- Weekly digest. Subscribed users get one curated paper every 7 days at 6 PM IST.
- YouTube links. Gemini pulls keywords from the query and the bot attaches related videos.
- Resumable ingestion. The scraper checkpoints its progress and records failures for each stage, so an interrupted run picks up where it stopped.
- Health checks. The bot tests its Pinecone connection periodically, which suits long-running hosted deployments.

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
| Scraper pipeline | `scraper/` | Scrape, summarize, embed and upsert articles |
| Telegram bot | `Bot/` | Query interface and scheduled digests |
| Container | `Dockerfile` | Bot deployment, for example on Hugging Face Spaces |

Both components use the same Pinecone index and the same embedding model (`all-MiniLM-L6-v2`, 384 dimensions).

## Pipeline results

A full ingestion run in August 2025 processed 15,557 articles. 15,145 succeeded and 412 failed, a 97.4% success rate. The failures were 165 in scraping, 165 in summarization and 24 in embedding. None failed at the Pinecone step.

## Prerequisites

- Python 3.11 or newer
- [Ollama](https://ollama.com/), for the scraper's summarization step
- A [Pinecone](https://www.pinecone.io/) account and a 384-dimension index using cosine similarity
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A Google Gemini API key
- A YouTube Data API v3 key

## Quick start

### 1. Clone and configure

```bash
git clone https://github.com/RohitDSonawane/ZenianResearchBot.git
cd ZenianResearchBot

cp scraper/.env.example scraper/.env
cp Bot/.env.example Bot/.env
```

Fill in your credentials in both `.env` files. `PINECONE_INDEX_NAME` has to be the same in both.

### 2. Run the scraper

```bash
cd scraper
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

# Ollama must be running with the configured model pulled
ollama pull gemma3:1b

python main.py
```

The scraper writes logs and checkpoints to `scraper/logs/`, which git ignores. You can stop it with `Ctrl+C` and it resumes from the last checkpoint.

### 3. Run the bot locally

```bash
cd Bot
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python query_bot.py
```

Send `/start` to the bot in Telegram, then send a research topic.

## Environment variables

Bot (`Bot/.env`):

| Variable | Description |
|----------|-------------|
| `TELEGRAM_TOKEN` | Telegram bot token |
| `GEMINI_API_KEY` | Google Gemini API key |
| `YOUTUBE_API_KEY` | YouTube Data API v3 key |
| `PINECONE_API_KEY` | Pinecone API key |
| `PINECONE_INDEX_NAME` | Pinecone index name (default `research-abstracts`) |

Scraper (`scraper/.env`). The full list is in `scraper/.env.example`. These are required:

| Variable | Description |
|----------|-------------|
| `PINECONE_API_KEY` | Pinecone API key |
| `PINECONE_INDEX_NAME` | Index name, same as the bot's |
| `OLLAMA_HOST` / `OLLAMA_PORT` | Address of the Ollama server |
| `OLLAMA_MODEL` | Model used for summaries |

## Deploying the bot

The `Dockerfile` builds and runs the Telegram bot:

```bash
docker build -t zenian-research-bot .
docker run --env-file Bot/.env zenian-research-bot
```

For [Hugging Face Spaces](https://huggingface.co/spaces), create a Docker Space and add `TELEGRAM_TOKEN`, `GEMINI_API_KEY`, `YOUTUBE_API_KEY`, `PINECONE_API_KEY` and `PINECONE_INDEX_NAME` as Space secrets. The bot polls Telegram and runs periodic health checks, so it works as a long-running Space.

The scraper needs Playwright and Ollama, so it runs on your own machine and is not in the Docker image.

## Project layout

```
ZenianResearchBot/
├── Bot/
│   ├── query_bot.py          Telegram bot entry point
│   ├── embedding_service.py  sentence-transformer embeddings
│   ├── pinecone_client.py    Pinecone query client
│   ├── requirements.txt
│   └── .env.example
├── scraper/
│   ├── main.py               ingestion pipeline entry point
│   ├── config.py             configuration and validation
│   ├── src/
│   │   ├── scraper.py        Playwright article scraper
│   │   ├── ollama_service.py summaries through Ollama
│   │   ├── pinecone_client.py
│   │   ├── embedding_service.py
│   │   └── utils.py
│   ├── requirements.txt
│   └── .env.example
├── Dockerfile
├── LICENSE
└── .github/workflows/ci.yml
```

## Limitations

- The scraper targets Springer Link search results. Follow the site's terms of service and rate limits, and tune `CONCURRENCY_LIMIT` and the wait settings to match.
- Search quality depends on how good the Ollama summaries are and on the `all-MiniLM-L6-v2` model.
- Weekly digest subscriptions are kept in memory by chat ID. Restarting the bot clears them until users message it again.

## Security

Never commit `.env` files or API keys. If a key has ever appeared in git history, rotate it in the provider's dashboard. Deleting it from the latest commit does not remove it from history.

## License

MIT. See [LICENSE](LICENSE).
