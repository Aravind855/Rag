"""
Cohere AI Embedding Module for NexaCore Knowledge Base RAG (Project 2).

Integrates Cohere's state-of-the-art `embed-english-v3.0` and `embed-multilingual-v3.0` models
via LlamaIndex's official `CohereEmbedding` (`llama-index-embeddings-cohere`).

Key Capabilities:
- Native support for search_document vs search_query asymmetric retrieval embeddings.
- Automatic rate-limiting and retry backoff for Cohere Trial Tier (HTTP 429 TooManyRequestsError).
- Global configuration hook into LlamaIndex `Settings.embed_model`.
"""

import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, List, Optional

from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.embeddings.cohere import CohereEmbedding

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("CohereEmbeddings")

# Model Constants
MODEL_COHERE_EMBED_ENGLISH_V3 = "embed-english-v3.0"
MODEL_COHERE_EMBED_MULTILINGUAL_V3 = "embed-multilingual-v3.0"
MODEL_COHERE_EMBED_ENGLISH_LIGHT_V3 = "embed-english-light-v3.0"

DEFAULT_EMBED_MODEL = os.getenv("COHERE_MODEL", MODEL_COHERE_EMBED_ENGLISH_V3)
DEFAULT_BATCH_SIZE = 40  # Cohere supports up to 96 texts per embed call


def get_cohere_api_key() -> str:
    """Retrieve Cohere API key from environment variables."""
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise ValueError(
            "COHERE_API_KEY not found in environment. "
            "Please ensure it is defined in d:\\RAG\\.env."
        )
    os.environ["COHERE_API_KEY"] = api_key
    return api_key


def format_retrieval_query(query: str, task_name: str = "search_query") -> str:
    """Clean and prepare query string for asymmetric search retrieval."""
    return query.strip()


def format_retrieval_document(content: str, title: Optional[str] = None) -> str:
    """Format document snippet with optional title prefix for retrieval indexing."""
    clean_content = content.strip()
    if title and title.strip():
        return f"{title.strip()}: {clean_content}"
    return clean_content


class RateLimitedCohereEmbedding(CohereEmbedding):
    """Subclass of CohereEmbedding providing robust batching and 429 rate limit backoff."""

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Batch document embeddings with automatic 429 retry backoff and gentle pacing."""
        results: List[List[float]] = []
        batch_size = min(self.embed_batch_size, 40)

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            for attempt in range(5):
                try:
                    batch_res = super()._get_text_embeddings(batch)
                    results.extend(batch_res)
                    time.sleep(0.2)  # Gentle pacing to avoid bursting trial tier quota
                    break
                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "TooManyRequests" in err_msg or "rate limit" in err_msg.lower():
                        wait_sec = 12 * (attempt + 1)
                        logger.warning(
                            f"Cohere Rate Limit (429) hit. Retrying in {wait_sec}s "
                            f"(Attempt {attempt + 1}/5)..."
                        )
                        time.sleep(wait_sec)
                    else:
                        raise e
        return results

    def _get_query_embedding(self, query: str) -> List[float]:
        """Query embedding with rate limit retry backoff."""
        for attempt in range(5):
            try:
                return super()._get_query_embedding(query)
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "TooManyRequests" in err_msg or "rate limit" in err_msg.lower():
                    wait_sec = 5 * (attempt + 1)
                    logger.warning(f"Cohere Rate Limit (429) on query embedding. Retrying in {wait_sec}s...")
                    time.sleep(wait_sec)
                else:
                    raise e
        return super()._get_query_embedding(query)


def get_embedding_model(
    model_name: str = DEFAULT_EMBED_MODEL,
    embed_batch_size: int = DEFAULT_BATCH_SIZE,
    api_key: Optional[str] = None,
    embedding_type: str = "float",
) -> CohereEmbedding:
    """Initialize and return a CohereEmbedding instance configured with rate-limiting backoff.

    Args:
        model_name: Cohere embedding model (default: 'embed-english-v3.0').
        embed_batch_size: Number of texts per API batch call (default: 40).
        api_key: Optional API key override.
        embedding_type: 'float' (default), 'int8', or 'binary'.

    Returns:
        Configured RateLimitedCohereEmbedding instance.
    """
    key = api_key or get_cohere_api_key()
    embed_model = RateLimitedCohereEmbedding(
        model_name=model_name,
        embed_batch_size=embed_batch_size,
        api_key=key,
        embedding_type=embedding_type,
    )
    logger.info(f"Initialized CohereEmbedding [model={model_name}, batch_size={embed_batch_size}, type={embedding_type}]")
    return embed_model


def configure_global_llamaindex_embeddings(
    embed_model: Optional[CohereEmbedding] = None,
    model_name: str = DEFAULT_EMBED_MODEL,
) -> CohereEmbedding:
    """Set global LlamaIndex Settings.embed_model to CohereEmbedding."""
    if embed_model is None:
        embed_model = get_embedding_model(model_name=model_name)

    Settings.embed_model = embed_model
    logger.info(f"Global LlamaIndex Settings.embed_model configured to: Cohere [{embed_model.model_name}]")
    return embed_model


if __name__ == "__main__":
    print("=" * 80)
    print(" NEXACORE KB RAG - COHERE AI EMBEDDING MODULE TEST (embed-english-v3.0)")
    print("=" * 80)

    try:
        embed_model = configure_global_llamaindex_embeddings(model_name=MODEL_COHERE_EMBED_ENGLISH_V3)

        # 1. Asymmetric Query Test (search_query input_type)
        raw_query = "What is NexaCore's policy on remote work eligibility?"
        query_vector = embed_model.get_query_embedding(raw_query)

        print(f"\n1. Asymmetric Query Embedding Test (input_type='search_query'):")
        print(f"   - Query           : '{raw_query}'")
        print(f"   - Vector Dimension: {len(query_vector)}")
        print(f"   - Vector Preview  : {query_vector[:5]}...")

        # 2. Asymmetric Document Batch Test (search_document input_type)
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
        print(f"\n2. Asymmetric Document Batch Embedding Test (input_type='search_document'):")
        print(f"   - Text Count     : {len(test_docs)}")
        print(f"   - Formatted Doc 1: '{test_docs[0]}'")
        print(f"   - Output Count   : {len(doc_vectors)}")
        print(f"   - Vector Size    : {len(doc_vectors[0])} dimensions each.")

        print("\n" + "=" * 80)
        print(" COHERE AI EMBEDDING MODULE TEST COMPLETED SUCCESSFULLY!")
        print("=" * 80)
    except Exception as ex:
        logger.error(f"Embedding Test Failed: {ex}")
        sys.exit(1)
