import os
import logging
import random
import re
import requests
import time
import asyncio
import pytz
from datetime import time as dt_time
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
import google.generativeai as genai

from embedding_service import EmbeddingService
from pinecone_client import PineconeQueryClient

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "research-abstracts")

if not TELEGRAM_TOKEN:
    raise ValueError("Missing TELEGRAM_TOKEN in your .env file.")
if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY in your .env file.")
if not YOUTUBE_API_KEY:
    raise ValueError("Missing YOUTUBE_API_KEY in your .env file.")
if not PINECONE_API_KEY:
    raise ValueError("Missing PINECONE_API_KEY in your .env file.")
if not PINECONE_INDEX_NAME:
    raise ValueError("Missing PINECONE_INDEX_NAME in your .env file.")

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("query_bot")

embedding_service = EmbeddingService()
pinecone_client = PineconeQueryClient()

chat_ids = set()

GREETINGS = [
    "hello", "hi", "hey", "heyy", "hii", "yo", "sup",
    "good morning", "good afternoon", "good evening",
    "bye", "goodbye", "see you", "take care",
]


def is_greeting(query: str) -> bool:
    q_lower = query.lower()
    return any(
        re.fullmatch(r"[\W_]*(" + re.escape(g) + r")[\W_]*", q_lower) or g in q_lower
        for g in GREETINGS
    )


def escape_html(text: str) -> str:
    if text is None:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def get_friendly_reply(user_text: str) -> str:
    try:
        prompt = (
            "Reply in 1-2 short lines, warmly and casually, to this greeting. "
            "Do not use emojis.\n\n"
            f"{user_text}"
        )
        response = gemini_model.generate_content(
            contents=[
                {"role": "user", "parts": [{"text": "You are a friendly Telegram chatbot."}]},
                {"role": "user", "parts": [{"text": prompt}]},
            ],
            generation_config={"temperature": 0.6},
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini error in get_friendly_reply: {e}")
        return random.choice([
            "Hi! How's your day going?",
            "Hey there! How can I help you today?",
            "Hello! Ready to explore some research papers?",
            "Hi! Feel free to ask about research topics.",
        ])


async def extract_keywords_with_llm(text, max_keywords=5):
    try:
        prompt = (
            f"Extract {max_keywords} research-relevant keywords or short phrases from this text, "
            f"suitable for YouTube video search.\n{text}\n"
            "List the keywords only, comma-separated."
        )
        response = gemini_model.generate_content(
            contents=[{"role": "user", "parts": [{"text": prompt}]}],
            generation_config={"temperature": 0.2, "max_output_tokens": 48},
        )
        keywords = response.text.strip()
        return [kw.strip() for kw in keywords.split(",") if kw.strip()]
    except Exception as e:
        logger.error(f"Gemini error in extract_keywords_with_llm: {e}")
        return []


async def generate_natural_intro(topic_text: str) -> str:
    try:
        prompt = (
            f"Generate a natural, casual introduction for sending a weekly research spark about this topic: "
            f"{topic_text}\n"
            "Make it 1-2 sentences. Do not use emojis. Vary the structure so it does not feel templated."
        )
        response = gemini_model.generate_content(
            contents=[{"role": "user", "parts": [{"text": prompt}]}],
            generation_config={"temperature": 0.8, "max_output_tokens": 100},
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini error in generate_natural_intro: {e}")
        return random.choice([
            "Here is this week's research spark for you:",
            "Check out this research topic:",
            "Here is something interesting in research this week:",
            "Thought you might like this research highlight:",
            "Here is a fresh research idea to spark your curiosity:",
        ])


async def get_first_youtube_links(keywords, max_results=3):
    if not keywords:
        return []
    yt_base_url = "https://www.googleapis.com/youtube/v3/search"
    collected = []
    for kw in keywords:
        params = {
            "part": "snippet",
            "q": kw,
            "type": "video",
            "maxResults": max_results,
            "key": YOUTUBE_API_KEY,
        }
        try:
            resp = requests.get(yt_base_url, params=params)
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("items", []):
                video_id = item["id"]["videoId"]
                url = f"https://www.youtube.com/watch?v={video_id}"
                if url not in collected:
                    collected.append(url)
                if len(collected) >= max_results:
                    return collected
        except Exception as e:
            logger.error(f"YouTube API error for keyword '{kw}': {e}")
    return collected


def _get_attr_or_key(obj, name, default=None):
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name, default)
    return default


async def send_research_spark(context):
    current_time = time.time()
    last_timestamp = pinecone_client.get_last_timestamp()
    if current_time - last_timestamp < 7 * 24 * 3600:
        logger.info("Skipping send: Last sent less than 7 days ago.")
        return

    general_query = "interesting research paper"
    vector = embedding_service.create_embeddings(general_query)
    if not vector:
        logger.error("Failed to create embedding for general query.")
        return

    matches = pinecone_client.query_top_k(vector, top_k=50)
    if not matches:
        logger.error("No papers found in Pinecone.")
        return

    article = random.choice(matches)
    meta = _get_attr_or_key(article, "metadata", {}) or {}
    title = (meta.get("title") or "[No title available]").strip()
    summary_raw = (meta.get("summary") or "[No summary available]").strip()
    link_url = meta.get("link") or "N/A"

    if len(summary_raw) > 400:
        summary_raw = summary_raw[:400].rstrip() + "..."

    title_escaped = escape_html(title)
    summary = escape_html(summary_raw)
    link_escaped = escape_html(link_url)

    if link_url.startswith("http"):
        link_html = f'<a href="{link_escaped}">Open Article</a>'
    else:
        link_html = link_escaped

    topic_text = f"{title}\n{summary_raw}"
    intro = await generate_natural_intro(topic_text)

    message = (
        f"{intro}\n\n"
        f"<b>Topic:</b> {title_escaped}\n"
        f"<b>Summary:</b> {summary}\n"
        f"<b>Link:</b> {link_html}"
    )

    try:
        keywords = await extract_keywords_with_llm(topic_text, max_keywords=3)
        if keywords:
            yt_links = await get_first_youtube_links(keywords, max_results=3)
            if yt_links:
                yt_message = "\n".join(
                    [f'<a href="{link}">Watch Video</a>' for link in yt_links]
                )
                message += "\n\n<b>Related YouTube Videos:</b>\n" + yt_message
    except Exception as e:
        logger.error(f"Error adding YouTube links: {e}")

    for chat_id in list(chat_ids):
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.error(f"Failed to send to chat_id {chat_id}: {e}")
            chat_ids.discard(chat_id)

    pinecone_client.update_timestamp(current_time)
    logger.info("Research spark sent and timestamp updated.")


async def start(update, context):
    chat_id = update.message.chat_id
    chat_ids.add(chat_id)
    await update.message.reply_text(
        "Hi! Send me a research topic and I will fetch the top matching paper.",
        parse_mode="HTML",
    )


async def handle_query(update, context):
    chat_id = update.message.chat_id
    chat_ids.add(chat_id)
    query_text = update.message.text.strip()

    if not query_text:
        await update.message.reply_text("Please send a valid query text.", parse_mode="HTML")
        return

    if is_greeting(query_text):
        reply = await get_friendly_reply(query_text)
        await update.message.reply_text(reply, parse_mode="HTML")
        return

    await update.message.reply_text("Searching for the most relevant paper...", parse_mode="HTML")

    vector = embedding_service.create_embeddings(query_text)
    if not vector:
        await update.message.reply_text("Failed to create embedding.", parse_mode="HTML")
        return

    matches = pinecone_client.query_top_k(vector, top_k=1)
    if not matches:
        await update.message.reply_text("No relevant papers found.", parse_mode="HTML")
        return

    top = matches[0]
    meta = _get_attr_or_key(top, "metadata", {}) or {}
    title = (meta.get("title") or "[No title available]").strip()
    summary_raw = (meta.get("summary") or "[No summary available]").strip()
    link_url = meta.get("link") or "N/A"

    if len(summary_raw) > 400:
        summary_raw = summary_raw[:400].rstrip() + "..."

    title_escaped = escape_html(title)
    summary = escape_html(summary_raw)
    link_escaped = escape_html(link_url)

    if link_url.startswith("http"):
        link_html = f'<a href="{link_escaped}">Open Article</a>'
    else:
        link_html = link_escaped

    message = (
        f"<b>Title:</b> {title_escaped}\n"
        f"<b>Summary:</b> {summary}\n"
        f"<b>Link:</b> {link_html}"
    )

    try:
        keyword_text = f"{title}\n{summary_raw}"
        keywords = await extract_keywords_with_llm(keyword_text, max_keywords=3)
        if not keywords:
            message += "\n\nCould not extract keywords for YouTube search."
        else:
            yt_links = await get_first_youtube_links(keywords, max_results=3)
            if yt_links:
                yt_message = "\n".join(
                    [f'<a href="{link}">Watch Video</a>' for link in yt_links]
                )
                message += "\n\n<b>Related YouTube Videos:</b>\n" + yt_message
            else:
                message += "\n\nNo relevant YouTube videos found."
    except Exception as e:
        logger.error(f"Error retrieving YouTube links: {e}")
        message += "\n\nFailed to retrieve YouTube videos due to an error."

    await update.message.reply_text(
        message,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def health_check(context):
    try:
        active_chats = len(chat_ids)
        logger.info(f"Bot health check: {active_chats} active chats")

        try:
            stats = await asyncio.to_thread(pinecone_client.describe_index_stats)
            logger.info(f"Pinecone health: {stats.total_vector_count} vectors")
        except Exception as e:
            logger.warning(f"Pinecone health check failed: {e}")
    except Exception as e:
        logger.error(f"Health check failed: {e}")


def main():
    logger.info("Starting Telegram bot...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query))

    if app.job_queue is None:
        logger.error(
            "JobQueue is not available. Install with: "
            'pip install "python-telegram-bot[job-queue]"'
        )
        raise RuntimeError("JobQueue dependency is missing.")

    app.job_queue.run_daily(
        send_research_spark,
        dt_time(18, 0, tzinfo=pytz.timezone("Asia/Kolkata")),
    )
    app.job_queue.run_repeating(health_check, interval=600, first=60)

    logger.info("Telegram bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
