# 🤖 ZenianResearchBot

> **Suggested GitHub description:** *AI-powered Telegram bot that scrapes Springer research papers, summarizes them with a local LLM, stores vector embeddings in Pinecone, and answers natural-language queries with relevant papers and YouTube videos.*

A comprehensive research paper discovery and query system that combines web scraping, LLM-powered summarization, vector embeddings, and a Telegram bot interface to make academic research accessible to everyone.

---

## 📖 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Technologies](#technologies)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Integrations](#api-integrations)
- [Docker](#docker)
- [Contributing](#contributing)
- [GitHub Repository Metadata](#github-repository-metadata)
- [License](#license)

---

## Overview

ZenianResearchBot is a two-component system:

1. **Scraper** — Automatically crawls research papers from Springer, generates LLM-based summaries, creates vector embeddings, and stores everything in a Pinecone vector database.
2. **Telegram Bot** — Provides a conversational interface where users can query the database by topic and receive relevant research papers complete with summaries and related YouTube video links.

Together, they form a pipeline that continuously ingests academic content and makes it searchable through natural-language queries in Telegram.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         SCRAPER PIPELINE                        │
│                                                                 │
│  Springer Website ──► Playwright Scraper ──► Ollama LLM         │
│        (search results)    (title, abstract,   (summarize +     │
│                             content)            embed)          │
│                                                    │            │
│                                                    ▼            │
│                                          Pinecone Vector DB     │
└─────────────────────────────────────────────────────────────────┘
                                  │
                            (stored vectors)
                                  │
┌─────────────────────────────────────────────────────────────────┐
│                          TELEGRAM BOT                           │
│                                                                 │
│  User Query ──► Sentence-Transformers ──► Pinecone Query        │
│   (text)         (encode to vector)       (similarity search)   │
│                                                    │            │
│                                                    ▼            │
│  Gemini API ◄──── Matched Papers ◄──── Top-K Results            │
│  (generate response +                              │            │
│   extract keywords)                                ▼            │
│       │                                  YouTube Data API       │
│       ▼                                  (related videos)       │
│  Telegram User ◄────────────────────────────────────────────────┘
│  (formatted response)
└─────────────────────────────────────────────────────────────────┘
```

---

## Features

### 🕷️ Scraper
- **Web Scraping** — Uses Playwright (headless Chromium) to extract article titles, abstracts, and content from Springer
- **Resource Optimization** — Blocks images, fonts, and stylesheets for faster page loads
- **LLM Summarization** — Uses a local Ollama model to generate concise ~150-word summaries
- **Vector Embeddings** — Generates text embeddings via Sentence-Transformers (`all-MiniLM-L6-v2`)
- **Vector Storage** — Upserts articles into Pinecone with metadata (title, summary, URL)
- **Duplicate Detection** — Checks Pinecone before processing to skip already-indexed articles
- **Concurrent Processing** — Processes multiple articles in parallel (configurable concurrency limit)
- **Checkpoint & Resume** — Saves progress to `logs/checkpoint.json`; resumes after interruption
- **Retry Logic** — Automatic retries with exponential backoff via `tenacity`
- **Pagination** — Iterates through multiple search result pages automatically

### 🤖 Telegram Bot
- **Semantic Search** — Finds relevant papers using cosine similarity on vector embeddings
- **Greeting Recognition** — Detects greetings and responds naturally instead of treating them as queries
- **AI-Powered Responses** — Uses Google Gemini to craft contextual, engaging replies
- **Research Paper Cards** — Returns top matching papers with title, summary, and source link
- **YouTube Integration** — Extracts keywords from results and fetches related YouTube videos
- **Daily Research Sparks** — Sends a random research paper to all active users every day at 6 PM IST
- **Health Monitoring** — Periodic health checks with internal logging
- **User Registration** — Tracks active chat IDs for broadcast messages

---

## Technologies

| Category | Technology |
|---|---|
| Language | Python 3.11 |
| Telegram | `python-telegram-bot` (with job-queue) |
| Web Scraping | Playwright (async) |
| HTML Parsing | BeautifulSoup4 |
| LLM (local) | Ollama (`gemma3:1b`) |
| LLM (cloud) | Google Generative AI (Gemini 1.5 Flash) |
| Embeddings | Sentence-Transformers (`all-MiniLM-L6-v2`) |
| Vector Database | Pinecone |
| HTTP Client | aiohttp |
| Async I/O | asyncio, aiofiles |
| Environment | python-dotenv |
| Retry Logic | tenacity |
| Timezone | pytz |
| Containerization | Docker |

---

## Project Structure

```
ZenianResearchBot/
├── dockerfile                     # Docker image for the Telegram bot
├── Bot/
│   ├── requirements.txt           # Bot Python dependencies
│   ├── query_bot.py               # Main Telegram bot application
│   ├── pinecone_client.py         # Pinecone similarity query wrapper
│   └── embedding_service.py       # Text-to-vector embedding helper
└── scraper/
    ├── requirements.txt           # Scraper Python dependencies
    ├── config.py                  # Central configuration and constants
    ├── main.py                    # Scraper orchestration & pipeline
    ├── logs/
    │   ├── checkpoint.json        # Resume checkpoint
    │   └── processing_stats.json  # Processing statistics
    └── src/
        ├── scraper.py             # Playwright-based web scraper
        ├── ollama_service.py      # Ollama LLM client (summarize + embed)
        ├── pinecone_client.py     # Pinecone upsert & duplicate-check client
        ├── embedding_service.py   # Sentence-Transformers embedding helper
        └── utils.py               # Logging, checkpointing, statistics
```

---

## Prerequisites

Before running either component, ensure you have:

- **Python 3.11+**
- **Ollama** — [Install from ollama.ai](https://ollama.ai) and pull required models:

  ```bash
  ollama pull gemma3:1b
  ollama pull all-minilm:latest
  ```

- **Pinecone** account and an index created at [pinecone.io](https://www.pinecone.io)
- **Telegram Bot Token** — Create a bot via [@BotFather](https://t.me/BotFather)
- **Google Gemini API Key** — [Get one from Google AI Studio](https://makersuite.google.com/app/apikey)
- **YouTube Data API v3 Key** — Enable via [Google Cloud Console](https://console.cloud.google.com)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/RohitDSonawane/ZenianResearchBot.git
cd ZenianResearchBot
```

### 2. Install Scraper dependencies

```bash
cd scraper
pip install -r requirements.txt
playwright install chromium
```

### 3. Install Bot dependencies

```bash
cd Bot
pip install -r requirements.txt
```

---

## Configuration

Create `.env` files in each component directory. **Never commit these files** (they are already listed in `.gitignore`).

### Scraper (`scraper/.env`)

```env
# Ollama (local LLM)
OLLAMA_HOST=localhost
OLLAMA_PORT=11434
OLLAMA_MODEL=gemma3:1b

# Pinecone
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=research-abstracts
EMBEDDING_DIMENSION=384

# Scraping
HEADLESS_MODE=true

# Performance
TEMPERATURE=0.3
MAX_TOKENS_FOR_SUMMARY=1000
CONCURRENCY_LIMIT=3
WAIT_BETWEEN_PAGES=5
WAIT_BETWEEN_ARTICLES=1.0

# Timeouts (milliseconds for browser, seconds for Ollama)
LAUNCH_TIMEOUT=60000
SCRAPING_TIMEOUT=90000
OLLAMA_TIMEOUT=180
```

### Bot (`Bot/.env`)

```env
TELEGRAM_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
YOUTUBE_API_KEY=your_youtube_data_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=research-abstracts
```

---

## Usage

### Running the Scraper

Ensure Ollama is running locally (`ollama serve`) and your `.env` file is configured.

```bash
cd scraper
python main.py
```

The scraper will:
1. Open pages from the configured Springer search URL
2. Extract article links from each page
3. For each article: scrape content → summarize via Ollama → embed → upsert to Pinecone
4. Save a checkpoint after each page so it can resume if interrupted

Progress and errors are logged to the `logs/` directory.

### Running the Telegram Bot

```bash
cd Bot
python query_bot.py
```

Then open Telegram and start a conversation with your bot:

| Input | Bot Response |
|---|---|
| `/start` | Welcome message + registers user for daily sparks |
| `Hello` / `Hi` / greeting | Friendly greeting response |
| Any research topic | Top matching research papers with summaries and YouTube videos |

**Scheduled features:**
- **Daily Research Spark** — Every day at **6:00 PM IST** the bot sends a random research paper to all registered users
- **Health Check** — Internal health check every 10 minutes

---

## API Integrations

| Service | Purpose |
|---|---|
| **Telegram Bot API** | Receive user messages, send formatted responses |
| **Google Gemini API** | Generate natural-language responses and extract keywords |
| **Pinecone** | Store and query vector embeddings for semantic search |
| **Ollama (local)** | Summarize articles and generate embeddings during scraping |
| **YouTube Data API v3** | Search for videos related to paper topics |
| **Springer** | Source of research paper content (scraped via Playwright) |

---

## Docker

A `dockerfile` is provided to containerize and run the **Telegram bot**:

```bash
# Build the image
docker build -t zenian-research-bot .

# Run the container with environment variables
docker run -d \
  -e TELEGRAM_TOKEN=your_telegram_bot_token \
  -e GEMINI_API_KEY=your_gemini_api_key \
  -e YOUTUBE_API_KEY=your_youtube_data_api_key \
  -e PINECONE_API_KEY=your_pinecone_api_key \
  -e PINECONE_INDEX_NAME=research-abstracts \
  --name research-bot \
  zenian-research-bot
```

> **Note:** The Dockerfile deploys only the bot component. The scraper is designed to be run separately, ideally as a periodic batch job or cron task.

---

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

Please ensure any API keys or secrets are kept out of commits and use `.env` files instead.

---

## GitHub Repository Metadata

### Suggested Repository Description

> AI-powered Telegram bot that scrapes Springer research papers, summarizes them with a local LLM (Ollama), stores vector embeddings in Pinecone, and answers natural-language queries with relevant papers and YouTube videos.

*(Set this in **GitHub → Repository Settings → Description**.)*

### Suggested Topics / Tags

```
telegram-bot  research-papers  web-scraping  llm  vector-database
pinecone  ollama  sentence-transformers  gemini-api  playwright
python  asyncio  rag  semantic-search  academic-research
springer  youtube-api  nlp  ai  chatbot
```

*(Add these in **GitHub → Repository Settings → Topics**.)*

---

## License

This project is open-source. See the repository for licensing details.

---

*Built with ❤️ by [RohitDSonawane](https://github.com/RohitDSonawane)*
