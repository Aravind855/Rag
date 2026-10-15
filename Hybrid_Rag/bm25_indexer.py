"""BM25 Sparse Retrieval & Indexing Module for Hybrid RAG (Functional Approach).

Loads pre-computed chunks from d:\RAG\Hybrid_Rag\chunks\chunks_manifest.json,
tokenizes them using a domain-aware tokenizer (preserving technical identifiers,
system IDs, numbers, and currency figures), builds a BM25Retriever,
and serializes the index to disk for rapid sparse retrieval.

All paths are resolved dynamically without hardcoding.
All operations are written as pure procedural functions without classes.
"""

import json
import logging
import os
from pathlib import Path
import pickle
import re
import time
from typing import Any, Dict, List, Optional, Sequence, Union

from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("hybrid_rag.bm25")

# =====================================================================
# DYNAMIC PATH RESOLUTION (NO HARDCODED PATHS)
# =====================================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CHUNKS_FILE = PROJECT_ROOT / "Hybrid_Rag" / "chunks" / "chunks_manifest.json"
DEFAULT_BM25_DIR = PROJECT_ROOT / "Hybrid_Rag" / "bm25"
DEFAULT_BM25_INDEX_FILE = DEFAULT_BM25_DIR / "bm25_index.pkl"


def get_default_chunks_file() -> Path:
    """Returns the dynamically resolved chunks manifest file path."""
    return DEFAULT_CHUNKS_FILE


def get_default_bm25_index_file() -> Path:
    """Returns the dynamically resolved BM25 index file path."""
    return DEFAULT_BM25_INDEX_FILE


# =====================================================================
# 1. DOMAIN-AWARE TOKENIZER (PRESERVES IDS, NUMBERS, TECHNICAL CODES)
# =====================================================================

def custom_bm25_tokenizer(text: str) -> List[str]:
    """Tokenizes text for BM25 indexing while strictly preserving:

    - Hyphenated / underscored entity IDs: SYS-001, BK-2026-0001, TRV-AIR, NC-ENG-API
    - Decimal numbers and percentages: 99.95%, 0.03, 10000, p95
    - Technical acronyms & policy terms: OIDC, SAML, JWT, RTO, RPO
    - Alphanumeric words
    """
    if not text:
        return []

    # Regex matches:
    # 1. Alphanumeric sequences containing hyphens or underscores (e.g. SYS-001, BK-2026-0001)
    # 2. Percentage expressions (e.g. 99.95%, 15%)
    # 3. Currency / numeric values (e.g. 10000, 50,000 -> 50000)
    # 4. Standard words
    token_pattern = re.compile(
        r"[a-zA-Z0-9]+(?:[-_][a-zA-Z0-9]+)+|\d+(?:\.\d+)?%?|[a-zA-Z0-9]+"
    )

    clean_text = text.lower().replace(",", "")  # remove commas in numbers like 50,000 -> 50000
    tokens = token_pattern.findall(clean_text)

    # Filter out empty or single punctuation tokens
    return [t for t in tokens if len(t) > 1 or t.isalnum()]


# =====================================================================
# 2. CHUNKS LOADER (DIRECT FROM JSON MANIFEST)
# =====================================================================
# verified
def load_chunks_for_indexing(
    chunks_path: Optional[Union[str, Path]] = None,
    ) -> List[Document]:
    """Loads all pre-computed chunks directly from chunks_manifest.json without re-chunking.

    Args:
        chunks_path: Path to chunks_manifest.json (defaults dynamically).

    Returns:
        List of LangChain Document objects.
    """
    manifest_file = Path(chunks_path).resolve() if chunks_path else DEFAULT_CHUNKS_FILE
    if not manifest_file.exists():
        raise FileNotFoundError(
            f"Chunks manifest not found at {manifest_file}. Please run chunking.py first."
        )

    logger.info(f"Loading chunks from manifest: {manifest_file}")
    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    raw_items = manifest_data.get("chunks", [])
    doc_chunks = [
        Document(
            page_content=item.get("content", ""),
            metadata=item.get("metadata", {}),
        )
        for item in raw_items
    ]

    logger.info(f"Loaded {len(doc_chunks)} chunks for BM25 indexing.")
    return doc_chunks


# =====================================================================
# 3. BM25 INDEX BUILDER & RETRIEVER FACTORY
# =====================================================================
# verified
def build_bm25_retriever(
    chunks: Sequence[Document],
    k: int = 5,
    k1: float = 1.5,
    b: float = 0.75,
    ) -> BM25Retriever:
    """Builds and tunes a LangChain BM25Retriever using the custom domain-aware tokenizer.

    Args:
        chunks: Sequence of LangChain Document objects.
        k: Default number of top documents to retrieve.
        k1: BM25 term frequency saturation parameter (default: 1.5).
        b: BM25 document length normalization parameter (default: 0.75).

    Returns:
        Fitted BM25Retriever instance.
    """
    if not chunks:
        raise ValueError("Cannot build BM25 retriever from empty chunks list.")

    logger.info(f"Building BM25 index over {len(chunks)} chunks with custom tokenizer...")
    start_time = time.time()

    retriever = BM25Retriever.from_documents(
        documents=list(chunks),
        preprocess_func=custom_bm25_tokenizer,
        k=k,
    )

    # Tune BM25 hyperparameters if underlying model exposes them
    if hasattr(retriever, "vectorizer") and retriever.vectorizer is not None:
        retriever.vectorizer.k1 = k1
        retriever.vectorizer.b = b

    elapsed = round(time.time() - start_time, 3)
    logger.info(f"BM25 index built successfully in {elapsed}s.")
    return retriever


# =====================================================================
# 4. SERIALIZATION & PERSISTENCE
# =====================================================================

def save_bm25_retriever(
    retriever: BM25Retriever,
    output_path: Optional[Union[str, Path]] = None,
    ) -> Path:
    """Serializes the fitted BM25Retriever to disk using pickle.

    Args:
        retriever: Fitted BM25Retriever object.
        output_path: Destination path (defaults to Hybrid_Rag/bm25/bm25_index.pkl).

    Returns:
        Path to the saved index file.
    """
    out_file = Path(output_path).resolve() if output_path else DEFAULT_BM25_INDEX_FILE
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(out_file, "wb") as f:
        pickle.dump(retriever, f)

    file_size_kb = round(out_file.stat().st_size / 1024, 2)
    logger.info(f"Serialized BM25 retriever to {out_file} ({file_size_kb} KB).")
    return out_file


def load_bm25_retriever(
    index_path: Optional[Union[str, Path]] = None,
    k: Optional[int] = None,
    ) -> BM25Retriever:
    """Loads a pre-built BM25Retriever from disk.

    Args:
        index_path: Path to serialized pickle file.
        k: Optional override for top-k retrieved documents.

    Returns:
        Ready-to-use BM25Retriever.
    """
    in_file = Path(index_path).resolve() if index_path else DEFAULT_BM25_INDEX_FILE
    if not in_file.exists():
        raise FileNotFoundError(f"BM25 index file not found at {in_file}. Run indexing first.")

    with open(in_file, "rb") as f:
        retriever = pickle.load(f)

    if k is not None:
        retriever.k = k

    return retriever


# =====================================================================
# 5. RETRIEVAL & QUERY FUNCTION
# =====================================================================

def sparse_search(
    query: str,
    retriever: Optional[BM25Retriever] = None,
    index_path: Optional[Union[str, Path]] = None,
    k: int = 5,
    ) -> List[Document]:
    """Performs sparse keyword retrieval using BM25.

    Args:
        query: User search query.
        retriever: Optional existing retriever instance (if None, loaded from disk).
        index_path: Optional path to index file.
        k: Number of chunks to retrieve.

    Returns:
        List of top-k ranked Document chunks.
    """
    active_retriever = retriever or load_bm25_retriever(index_path=index_path, k=k)
    active_retriever.k = k

    start_time = time.time()
    results = active_retriever.invoke(query)
    latency_ms = round((time.time() - start_time) * 1000, 2)

    logger.info(f"BM25 retrieved {len(results)} chunks for query='{query}' in {latency_ms} ms")
    return results


# =====================================================================
# 6. PIPELINE ORCHESTRATOR
# =====================================================================

def run_bm25_indexing(
    chunks_path: Optional[Union[str, Path]] = None,
    output_path: Optional[Union[str, Path]] = None,
    k: int = 5,
    ) -> Dict[str, Any]:
    """End-to-end procedural pipeline:

    1. Loads chunks directly from chunks_manifest.json
    2. Builds BM25Retriever using domain-aware tokenizer
    3. Serializes the fitted retriever to disk
    4. Runs validation queries to verify keyword retrieval
    """
    logger.info("=" * 70)
    logger.info("STARTING HYBRID RAG BM25 SPARSE INDEXING PIPELINE")
    logger.info("=" * 70)

    # 1. Load chunks
    chunks = load_chunks_for_indexing(chunks_path)

    # 2. Build index
    retriever = build_bm25_retriever(chunks=chunks, k=k)

    # 3. Save index
    saved_path = save_bm25_retriever(retriever=retriever, output_path=output_path)

    # 4. Verification queries
    test_queries = [
        "SYS-001",
        "domestic airfare limit",
        "Tier-1 incident response",
    ]

    verification_results = {}
    for q in test_queries:
        hits = sparse_search(q, retriever=retriever, k=2)
        top_hit = hits[0] if hits else None
        verification_results[q] = {
            "top_chunk_id": top_hit.metadata.get("chunk_id") if top_hit else None,
            "top_breadcrumbs": top_hit.metadata.get("breadcrumbs") if top_hit else None,
            "snippet": top_hit.page_content[:120].replace("\n", " ") if top_hit else None,
        }

    logger.info("=" * 70)
    logger.info("[BM25 SPARSE INDEXING COMPLETE]")
    logger.info(f"Total Indexed Chunks : {len(chunks)}")
    logger.info(f"Index File Saved To  : {saved_path}")
    logger.info("Sample Query Hits:")
    for query, res in verification_results.items():
        logger.info(f" • '{query}' -> [{res['top_chunk_id']}] {res['snippet']}...")
    logger.info("=" * 70)

    return {
        "total_chunks": len(chunks),
        "index_file": str(saved_path),
        "verification_results": verification_results,
    }


if __name__ == "__main__":
    run_bm25_indexing()
