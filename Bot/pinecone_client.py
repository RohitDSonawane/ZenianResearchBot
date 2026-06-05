import logging
from pinecone import Pinecone
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger('query_bot.pinecone')

EMBEDDING_DIM = 384


class PineconeQueryClient:
    def __init__(self):
        api_key = os.getenv("PINECONE_API_KEY")
        index_name = os.getenv("PINECONE_INDEX_NAME")
        if not api_key or not index_name:
            raise ValueError("Missing PINECONE_API_KEY or PINECONE_INDEX_NAME in .env")
        self.pc = Pinecone(api_key=api_key)
        self.index = self.pc.Index(index_name)

    def query_top_k(self, vector, top_k=10):
        try:
            results = self.index.query(vector=vector, top_k=top_k, include_metadata=True)
            return results.matches
        except Exception as e:
            logger.error(f"Error querying Pinecone: {e}")
            return []

    def get_last_timestamp(self):
        try:
            response = self.index.fetch(ids=["last_sent"])
            if response.get("vectors") and "last_sent" in response["vectors"]:
                return response["vectors"]["last_sent"]["metadata"].get("timestamp", 0)
            return 0
        except Exception as e:
            logger.error(f"Pinecone fetch error: {e}")
            return 0

    def update_timestamp(self, ts):
        try:
            zero_vector = [0.0] * EMBEDDING_DIM
            self.index.upsert(vectors=[{
                "id": "last_sent",
                "values": zero_vector,
                "metadata": {"timestamp": ts},
            }])
        except Exception as e:
            logger.error(f"Pinecone upsert error: {e}")

    def describe_index_stats(self):
        return self.index.describe_index_stats()
