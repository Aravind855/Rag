"""Cohere Embedding Service for Hybrid RAG (Functional Approach).

Configures and initializes CohereEmbeddings using environment variables
(COHERE_API_KEY and COHERE_EMBEDDING_MODEL='embed-v5.0-fast') from .env.
Provides pure, standalone functions to embed queries, embed document chunks in batches,
and cache embedded vectors for downstream Vector Database indexing.

All paths are resolved dynamically without hardcoding.
All operations are written as pure procedural functions without classes.
"""

import json
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Sequence, Union

from dotenv import load_dotenv
from langchain_cohere import CohereEmbeddings
from langchain_core.documents import Document

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("hybrid_rag.embeddings")

# =====================================================================
# DYNAMIC PATH RESOLUTION & ENVIRONMENT LOADING
# =====================================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

DEFAULT_CHUNKS_FILE = PROJECT_ROOT / "Hybrid_Rag" / "chunks" / "chunks_manifest.json"
DEFAULT_EMBEDDINGS_CACHE = PROJECT_ROOT / "Hybrid_Rag" / "chunks" / "embedded_chunks.json"


def get_project_root() -> Path:
    """Returns the dynamically resolved project root directory."""
    return PROJECT_ROOT


# =====================================================================
# EMBEDDING MODEL INITIALIZATION (FUNCTIONAL)
# =====================================================================
#verified
def get_cohere_embeddings(
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    ) -> CohereEmbeddings:
    """Initializes and returns a LangChain CohereEmbeddings instance.

    Reads model and API key from environment variables with fallback defaults.
    """
    key = api_key or os.getenv("COHERE_API_KEY")
    if not key:
        raise ValueError("COHERE_API_KEY is not set in environment or .env file.")

    model = model_name or os.getenv("COHERE_EMBEDDING_MODEL", "embed-v5.0-fast")

    logger.info(f"Initializing CohereEmbeddings with model='{model}'...")
    return CohereEmbeddings(
        cohere_api_key=key,
        model=model,
    )


# =====================================================================
# CORE EMBEDDING FUNCTIONS
# =====================================================================

def embed_query_text(
    query: str,
    embeddings: Optional[CohereEmbeddings] = None,
    ) -> List[float]:
    """Generates an embedding vector for a single search query text.

    Args:
        query: Query string.
        embeddings: Optional existing CohereEmbeddings instance.

    Returns:
        List of floats representing the query embedding vector.
    """
    emb = embeddings or get_cohere_embeddings()
    return emb.embed_query(query)


def embed_document_texts(
    texts: List[str],
    embeddings: Optional[CohereEmbeddings] = None,
    batch_size: int = 64,
    ) -> List[List[float]]:
    """Generates embeddings for multiple document texts using batching.

    Cohere API limits batch sizes per request (max 96), so batching ensures
    safe, uninterrupted embedding generation.

    Args:
        texts: List of text strings to embed.
        embeddings: Optional existing CohereEmbeddings instance.
        batch_size: Number of texts per batch request (default: 64).

    Returns:
        List of embedding vectors.
    """
    if not texts:
        return []

    emb = embeddings or get_cohere_embeddings()
    all_embeddings: List[List[float]] = []
    total = len(texts)

    logger.info(f"Generating embeddings for {total} texts in batches of {batch_size}...")

    for i in range(0, total, batch_size):
        batch = texts[i : i + batch_size]
        batch_idx = (i // batch_size) + 1
        total_batches = (total + batch_size - 1) // batch_size
        logger.info(f"Embedding batch {batch_idx}/{total_batches} ({len(batch)} texts)...")

        batch_vectors = emb.embed_documents(batch)
        all_embeddings.extend(batch_vectors)

        # Brief rate-limiting pause between batches if multiple batches
        if total_batches > 1:
            time.sleep(0.2)

    logger.info(f"Completed embedding {len(all_embeddings)} texts successfully.")
    return all_embeddings


def embed_document_chunks(
    chunks: Sequence[Document],
    embeddings: Optional[CohereEmbeddings] = None,
    batch_size: int = 64,
    ) -> List[Dict[str, Any]]:
    """Takes a list of LangChain Document chunks, generates Cohere embeddings,

    and associates each chunk with its embedding vector and metadata.

    Args:
        chunks: Sequence of LangChain Document objects.
        embeddings: Optional CohereEmbeddings instance.
        batch_size: Batch size for API calls.

    Returns:
        List of dictionaries containing chunk_id, content, metadata, and embedding vector.
    """
    if not chunks:
        logger.warning("No chunks provided to embed.")
        return []

    emb = embeddings or get_cohere_embeddings()
    texts = [doc.page_content for doc in chunks]

    start_time = time.time()
    vectors = embed_document_texts(texts=texts, embeddings=emb, batch_size=batch_size)
    elapsed = round(time.time() - start_time, 2)

    embedded_chunks: List[Dict[str, Any]] = []
    for doc, vec in zip(chunks, vectors):
        meta = dict(doc.metadata)
        embedded_chunks.append({
            "chunk_id": meta.get("chunk_id"),
            "content": doc.page_content,
            "metadata": meta,
            "embedding": vec,
            "embedding_model": emb.model,
            "embedding_dimension": len(vec),
        })

    logger.info(f"Successfully embedded {len(embedded_chunks)} chunks in {elapsed}s (Dim: {len(vectors[0])}).")
    return embedded_chunks


# =====================================================================
# CACHING & PERSISTENCE FUNCTIONS
# =====================================================================

def save_embedded_chunks_to_json(
    embedded_chunks: List[Dict[str, Any]],
    output_path: Optional[Union[str, Path]] = None,
    ) -> Path:
    """Caches embedded chunks with vectors and metadata to disk.

    Avoids redundant API calls and allows immediate ingestion into Vector Databases.
    """
    out_file = Path(output_path).resolve() if output_path else DEFAULT_EMBEDDINGS_CACHE
    out_file.parent.mkdir(parents=True, exist_ok=True)

    summary_data = {
        "total_chunks": len(embedded_chunks),
        "embedding_model": embedded_chunks[0]["embedding_model"] if embedded_chunks else "unknown",
        "embedding_dimension": embedded_chunks[0]["embedding_dimension"] if embedded_chunks else 0,
        "chunks": embedded_chunks,
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    logger.info(f"Cached {len(embedded_chunks)} embedded chunks to {out_file}")
    return out_file


def load_embedded_chunks_from_json(
    input_path: Optional[Union[str, Path]] = None,
    ) -> List[Dict[str, Any]]:
    """Loads precomputed embedded chunks from disk cache."""
    in_file = Path(input_path).resolve() if input_path else DEFAULT_EMBEDDINGS_CACHE
    if not in_file.exists():
        logger.error(f"Embeddings cache file does not exist: {in_file}")
        return []

    with open(in_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("chunks", [])


# =====================================================================
# CHUNK EMBEDDING PIPELINE (PROCESS & EMBED ALL CHUNKS)
# =====================================================================

def process_and_embed_all_chunks(
    chunks_path: Optional[Union[str, Path]] = None,
    output_path: Optional[Union[str, Path]] = None,
    batch_size: int = 64,
    ) -> List[Dict[str, Any]]:
    """Loads all document chunks, generates Cohere embeddings,

    and saves the embedded vectors to disk for vector database indexing.

    Args:
        chunks_path: Path to chunks_manifest.json (defaults dynamically).
        output_path: Path to save embedded_chunks.json (defaults dynamically).
        batch_size: Batch size for Cohere embed API calls (default: 64).

    Returns:
        List of dictionaries with chunk_id, content, metadata, and embedding vector.
    """
    manifest_file = Path(chunks_path).resolve() if chunks_path else DEFAULT_CHUNKS_FILE

    # If chunks manifest does not exist, generate chunks dynamically using chunking module
    if not manifest_file.exists():
        logger.info(f"Chunks manifest not found at {manifest_file}. Generating chunks first...")
        from chunking import chunk_all_documents, save_chunks_to_json
        doc_chunks = chunk_all_documents()
        save_chunks_to_json(doc_chunks, manifest_file)
    else:
        logger.info(f"Loading chunks from manifest: {manifest_file}")
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
        raw_items = manifest_data.get("chunks", [])
        doc_chunks = [
            Document(page_content=item.get("content", ""), metadata=item.get("metadata", {}))
            for item in raw_items
        ]

    logger.info(f"Loaded {len(doc_chunks)} chunks for embedding.")

    # Initialize Cohere embeddings
    embeddings = get_cohere_embeddings()

    # Generate embeddings across all chunks
    embedded_chunks = embed_document_chunks(
        chunks=doc_chunks,
        embeddings=embeddings,
        batch_size=batch_size,
    )

    # Save to disk cache
    out_file = save_embedded_chunks_to_json(embedded_chunks, output_path=output_path)

    logger.info("=" * 70)
    logger.info("[CHUNKS EMBEDDING COMPLETE]")
    logger.info(f"Total Chunks Embedded : {len(embedded_chunks)}")
    logger.info(f"Embedding Model       : {embeddings.model}")
    logger.info(f"Vector Dimension      : {embedded_chunks[0]['embedding_dimension'] if embedded_chunks else 0}")
    logger.info(f"Saved To File         : {out_file}")
    logger.info("=" * 70)

    return embedded_chunks


if __name__ == "__main__":
    process_and_embed_all_chunks()
