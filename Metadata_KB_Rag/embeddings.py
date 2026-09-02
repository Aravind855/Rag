"""
Google GenAI Embedding Module for NexaCore Knowledge Base RAG (Project 2).

Integrates Google's latest `gemini-embedding-2` and `gemini-embedding-001` models via
LlamaIndex's official `GoogleGenAIEmbedding` (`llama-index-embeddings-google-genai`).

Supports:
- Multimodal & Text Embedding Generation (`gemini-embedding-2` and `gemini-embedding-001`)
- Task-type prompt instructions for asymmetric retrieval (`task: search result | query: ...`)
- Automatic rate-limiting and retry backoff for Google Free Tier (HTTP 429)
"""

import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, List, Optional

from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("GoogleGenAIEmbeddings")

# Model Constants
MODEL_GEMINI_EMBEDDING_2 = "models/gemini-embedding-2"
MODEL_GEMINI_EMBEDDING_1 = "models/gemini-embedding-001"

DEFAULT_EMBED_MODEL = MODEL_GEMINI_EMBEDDING_2
DEFAULT_BATCH_SIZE = 20


def get_google_api_key() -> str:
    """Retrieve Google/Gemini API key from environment variables."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY or GOOGLE_API_KEY not found in environment. "
            "Please ensure it is defined in d:\\RAG\\.env."
        )
    os.environ["GEMINI_API_KEY"] = api_key
    os.environ["GOOGLE_API_KEY"] = api_key
    return api_key


def format_retrieval_query(query: str, task_name: str = "search result") -> str:
    """Format search query for gemini-embedding-2 asymmetric retrieval tasks.

    Example output: 'task: search result | query: What is the remote work policy?'
    """
    clean_query = query.strip()
    return f"task: {task_name} | query: {clean_query}"


def format_retrieval_document(content: str, title: Optional[str] = None) -> str:
    """Format document snippet for gemini-embedding-2 asymmetric retrieval tasks.

    Example output: 'title: Remote Work Policy | text: Employees get 12 days...'
    """
    clean_content = content.strip()
    clean_title = title.strip() if title else "none"
    return f"title: {clean_title} | text: {clean_content}"


class RateLimitedGoogleGenAIEmbedding(GoogleGenAIEmbedding):
    """Subclass of GoogleGenAIEmbedding providing robust batching & 429 rate limit backoff."""

    def _embed_texts(self, texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
        """Override internal embedding call with rate-limit retry logic."""
        results: List[List[float]] = []
        batch_size = DEFAULT_BATCH_SIZE

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            for attempt in range(5):
                try:
                    batch_res = super()._embed_texts(batch, task_type=task_type)
                    results.extend(batch_res)
                    time.sleep(0.3)  # Gentle pacing to respect API quota
                    break
                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "Quota exceeded" in err_msg:
                        wait_sec = 15 * (attempt + 1)
                        logger.warning(
                            f"Google GenAI Rate Limit (429) hit. Retrying in {wait_sec}s "
                            f"(Attempt {attempt + 1}/5)..."
                        )
                        time.sleep(wait_sec)
                    else:
                        raise e
        return results


def get_embedding_model(
    model_name: str = DEFAULT_EMBED_MODEL,
    embed_batch_size: int = DEFAULT_BATCH_SIZE,
    api_key: Optional[str] = None,
) -> GoogleGenAIEmbedding:
    """Initialize and return a GoogleGenAIEmbedding instance configured with rate-limiting backoff.

    Args:
        model_name: Google embedding model ('models/gemini-embedding-2' or 'models/gemini-embedding-001').
        embed_batch_size: Number of texts per API batch call (default: 20).
        api_key: Optional API key override.

    Returns:
        Configured RateLimitedGoogleGenAIEmbedding instance.
    """
    key = api_key or get_google_api_key()
    embed_model = RateLimitedGoogleGenAIEmbedding(
        model_name=model_name,
        embed_batch_size=embed_batch_size,
        api_key=key,
    )
    logger.info(f"Initialized GoogleGenAIEmbedding [model={model_name}, batch_size={embed_batch_size}]")
    return embed_model


def configure_global_llamaindex_embeddings(
    embed_model: Optional[GoogleGenAIEmbedding] = None,
    model_name: str = DEFAULT_EMBED_MODEL,
) -> GoogleGenAIEmbedding:
    """Set global LlamaIndex Settings.embed_model to GoogleGenAIEmbedding."""
    if embed_model is None:
        embed_model = get_embedding_model(model_name=model_name)

    Settings.embed_model = embed_model
    logger.info(f"Global LlamaIndex Settings.embed_model configured to: {embed_model.model_name}")
    return embed_model


if __name__ == "__main__":
    print("=" * 80)
    print(" NEXACORE KB RAG - GOOGLE GENAI EMBEDDING MODULE TEST (gemini-embedding-2)")
    print("=" * 80)

    try:
        embed_model = configure_global_llamaindex_embeddings(model_name=MODEL_GEMINI_EMBEDDING_2)

        # Query Test with Task Formatting
        raw_query = "What is NexaCore's policy on remote work eligibility?"
        formatted_query = format_retrieval_query(raw_query)
        query_vector = embed_model.get_query_embedding(formatted_query)

        print(f"\n1. Asymmetric Query Embedding Test:")
        print(f"   - Formatted Query: '{formatted_query}'")
        print(f"   - Vector Dimension: {len(query_vector)}")
        print(f"   - Vector Preview  : {query_vector[:5]}...")

        # Document Batch Test with Document Task Formatting
        test_docs = [
            format_retrieval_document(
                "Employees are eligible for remote work after 90 days of onboarding.",
                title="Remote Work Eligibility",
            ),
            format_retrieval_document(
                "All remote staff must maintain core hours of 10 AM to 4 PM EST.",
                title="Working Hours",
            ),
        ]
        doc_vectors = embed_model.get_text_embedding_batch(test_docs)
        print(f"\n2. Asymmetric Document Batch Embedding Test:")
        print(f"   - Text Count     : {len(test_docs)}")
        print(f"   - Formatted Doc 1: '{test_docs[0]}'")
        print(f"   - Output Count   : {len(doc_vectors)}")
        print(f"   - Vector Size    : {len(doc_vectors[0])} dimensions each.")

        print("\n" + "=" * 80)
        print(" GOOGLE GENAI EMBEDDING MODULE TEST COMPLETED SUCCESSFULLY!")
        print("=" * 80)
    except Exception as ex:
        logger.error(f"Embedding Test Failed: {ex}")
        sys.exit(1)
