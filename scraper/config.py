import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger('article_scraper.config')

load_dotenv()

class Config:
    # Ollama Configuration
    OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'localhost')
    OLLAMA_PORT = os.getenv('OLLAMA_PORT', '11434')
    OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'gemma3:1b')

    # Ollama Generation Parameters
    TEMPERATURE = float(os.getenv('TEMPERATURE', '0.3'))
    MAX_TOKENS_FOR_SUMMARY = int(os.getenv('MAX_TOKENS_FOR_SUMMARY', '1000'))
    TOP_P = float(os.getenv('TOP_P', '0.9'))
    TOP_K = int(os.getenv('TOP_K', '40'))

    # Pinecone Configuration
    PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
    PINECONE_ENVIRONMENT = os.getenv('PINECONE_ENVIRONMENT', 'us-east-1')
    PINECONE_INDEX_NAME = os.getenv('PINECONE_INDEX_NAME', 'research-abstracts')
    EMBEDDING_DIMENSION = int(os.getenv('EMBEDDING_DIMENSION', '384'))

    # Scraping Configuration
    BASE_SEARCH_URL = os.getenv(
        'BASE_SEARCH_URL',
        'https://link.springer.com/search?new-search=true&query=research&dateFrom=&dateTo=&sortBy=relevance',
    )
    HEADLESS_MODE = os.getenv('HEADLESS_MODE', 'true').lower() == 'true'
    USER_AGENT = os.getenv(
        'USER_AGENT',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    )

    # Timeout Settings
    LAUNCH_TIMEOUT = int(os.getenv('LAUNCH_TIMEOUT', '60000'))
    SCRAPING_TIMEOUT = int(os.getenv('SCRAPING_TIMEOUT', '90000'))
    OLLAMA_TIMEOUT = int(os.getenv('OLLAMA_TIMEOUT', '180'))

    # Concurrency and Rate Limiting
    CONCURRENCY_LIMIT = int(os.getenv('CONCURRENCY_LIMIT', '3'))
    WAIT_BETWEEN_PAGES = int(os.getenv('WAIT_BETWEEN_PAGES', '5'))
    WAIT_BETWEEN_ARTICLES = float(os.getenv('WAIT_BETWEEN_ARTICLES', '1.0'))

    # File Paths
    LOGS_DIR = os.getenv('LOGS_DIR', 'logs')
    MAIN_LOG_FILE = os.path.join(LOGS_DIR, 'main.log')
    FAILED_ARTICLES_FILE = os.path.join(LOGS_DIR, 'failed_articles.log')
    STATS_FILE = os.path.join(LOGS_DIR, 'processing_stats.json')
    CHECKPOINT_FILE = os.path.join(LOGS_DIR, 'checkpoint.json')

    @classmethod
    def validate(cls):
        logger.info("Validating configuration...")
        errors = []
        if not cls.PINECONE_API_KEY:
            errors.append("PINECONE_API_KEY is required")
        if not cls.PINECONE_INDEX_NAME:
            errors.append("PINECONE_INDEX_NAME is required")
        if cls.EMBEDDING_DIMENSION <= 0:
            errors.append("EMBEDDING_DIMENSION must be a positive integer")
        if errors:
            raise ValueError("Configuration errors: " + "; ".join(errors))
        logger.info("Configuration validated successfully")
        return True
