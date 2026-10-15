"""Dense and Sparse Retrieval Module for Hybrid RAG (Functional Approach).

Implements independent dense and sparse retrieval strategies:
1. Dense Retrieval: Cohere query embeddings (embed-v5.0-fast) + Qdrant HNSW graph search.
2. Sparse Retrieval: Domain-aware tokenization + BM25 inverted index search.
3. Dual Retrieval: Fetches candidates from both streams, ready for downstream fusion and reranking.

All paths are resolved dynamically without hardcoding.
All operations are written as pure procedural functions without classes.
"""

import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Sequence, Union

from dotenv import load_dotenv
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.http.models import SearchParams

# Functional imports from local modules
from bm25_indexer import custom_bm25_tokenizer, load_bm25_retriever
from embeddings import embed_query_text, get_cohere_embeddings
from qdrant_indexer import (
    DEFAULT_COLLECTION_NAME,
    get_qdrant_client,
    get_qdrant_retriever,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("hybrid_rag.retriever")

# =====================================================================
# DYNAMIC PATH RESOLUTION & ENVIRONMENT LOADING
# =====================================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

DEFAULT_BM25_INDEX_FILE = PROJECT_ROOT / "Hybrid_Rag" / "bm25" / "bm25_index.pkl"


def get_default_bm25_index_file() -> Path:
    """Returns the dynamically resolved BM25 index file path."""
    return DEFAULT_BM25_INDEX_FILE


# =====================================================================
# 1. DENSE RETRIEVAL STRATEGY (COHERE + QDRANT HNSW)
# =====================================================================

def retrieve_dense(
    query: str,
    k: int = 5,
    hnsw_ef: int = 64,
    client: Optional[QdrantClient] = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    ) -> List[Document]:
    """Retrieves top-k semantically similar chunks from Qdrant using Cohere embeddings.

    Executes HNSW approximate nearest neighbor search via Qdrant's graph index.

    Args:
        query: User search query.
        k: Number of top documents to retrieve (default: 5).
        hnsw_ef: Dynamic search candidate beam size in the HNSW graph (default: 64).
        client: Optional existing QdrantClient instance.
        collection_name: Qdrant collection name (defaults to 'nexacore_dense_chunks').

    Returns:
        List of ranked LangChain Document objects with dense metadata.
    """
    if not query.strip():
        logger.warning("Empty query passed to retrieve_dense.")
        return []

    start_time = time.time()
    q_client = client or get_qdrant_client()[0]

    # Generate query embedding using Cohere (embed-v5.0-fast, 2048-dim)
    query_vector = embed_query_text(query)

    # Execute HNSW search on Qdrant
    search_params = SearchParams(hnsw_ef=hnsw_ef, exact=False)
    search_result = q_client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=k,
        search_params=search_params,
        with_payload=True,
    )

    retrieved_docs: List[Document] = []
    for rank, point in enumerate(search_result.points, start=1):
        payload = point.payload or {}
        content = payload.get("page_content", "")
        meta = dict(payload.get("metadata", {}))

        # Attach retrieval diagnostic metadata
        meta.update({
            "retrieval_mode": "dense",
            "dense_rank": rank,
            "dense_score": round(float(point.score), 4),
            "point_id": point.id,
            "breadcrumbs": payload.get("breadcrumbs", meta.get("breadcrumbs", "")),
            "chunk_id": payload.get("chunk_id", meta.get("chunk_id", "")),
        })

        retrieved_docs.append(Document(page_content=content, metadata=meta))

    latency_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(f"[Dense Retrieval] Retrieved {len(retrieved_docs)} chunks for '{query[:40]}' in {latency_ms} ms")
    return retrieved_docs


# =====================================================================
# 2. SPARSE RETRIEVAL STRATEGY (DOMAIN-AWARE BM25)
# =====================================================================

def retrieve_sparse(
    query: str,
    k: int = 5,
    index_path: Optional[Union[str, Path]] = None,
    retriever: Optional[BM25Retriever] = None,
    ) -> List[Document]:
    """Retrieves top-k lexically matching chunks from the BM25 inverted index.

    Tokenizes query with custom domain-aware tokenizer to preserve exact
    technical IDs (SYS-001, TRV-AIR), codes, numbers, and currencies.

    Args:
        query: User search query.
        k: Number of top documents to retrieve (default: 5).
        index_path: Optional path to serialized BM25 index pickle file.
        retriever: Optional pre-loaded BM25Retriever instance.

    Returns:
        List of ranked LangChain Document objects with sparse metadata.
    """
    if not query.strip():
        logger.warning("Empty query passed to retrieve_sparse.")
        return []

    start_time = time.time()
    active_retriever = retriever or load_bm25_retriever(index_path=index_path, k=k)
    active_retriever.k = k

    # Perform BM25 lexical search
    raw_results = active_retriever.invoke(query)

    retrieved_docs: List[Document] = []
    for rank, doc in enumerate(raw_results[:k], start=1):
        meta = dict(doc.metadata)
        meta.update({
            "retrieval_mode": "sparse",
            "sparse_rank": rank,
            "breadcrumbs": meta.get("breadcrumbs", ""),
            "chunk_id": meta.get("chunk_id", ""),
        })
        retrieved_docs.append(Document(page_content=doc.page_content, metadata=meta))

    latency_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(f"[Sparse Retrieval] Retrieved {len(retrieved_docs)} chunks for '{query[:40]}' in {latency_ms} ms")
    return retrieved_docs


# =====================================================================
# 3. DUAL RETRIEVAL (DENSE + SPARSE CANDIDATE POOL)
# =====================================================================

def retrieve_both(
    query: str,
    dense_k: int = 5,
    sparse_k: int = 5,
    hnsw_ef: int = 64,
    qdrant_client: Optional[QdrantClient] = None,
    bm25_retriever: Optional[BM25Retriever] = None,
    ) -> Dict[str, List[Document]]:
    """Executes both dense and sparse retrieval in parallel or sequence,

    returning the separate candidate sets without fusion or reranking.

    Args:
        query: User search query.
        dense_k: Number of dense candidates to retrieve.
        sparse_k: Number of sparse candidates to retrieve.
        hnsw_ef: HNSW search beam size.
        qdrant_client: Optional QdrantClient.
        bm25_retriever: Optional BM25Retriever.

    Returns:
        Dictionary containing:
        {
            "dense": List[Document],
            "sparse": List[Document]
        }
    """
    start_time = time.time()

    dense_candidates = retrieve_dense(
        query=query,
        k=dense_k,
        hnsw_ef=hnsw_ef,
        client=qdrant_client,
    )

    sparse_candidates = retrieve_sparse(
        query=query,
        k=sparse_k,
        retriever=bm25_retriever,
    )

    total_latency_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(
        f"[Dual Retrieval] Total {len(dense_candidates)} dense + {len(sparse_candidates)} sparse "
        f"candidates fetched in {total_latency_ms} ms"
    )

    return {
        "dense": dense_candidates,
        "sparse": sparse_candidates,
    }


# =====================================================================
# 4. INSPECTION & FORMATTING HELPER
# =====================================================================

def format_retrieval_summary(docs: Sequence[Document], mode_label: str = "Results") -> str:
    """Formats retrieved Document chunks into a readable summary table/list."""
    lines = [f"\n=== {mode_label.upper()} ({len(docs)} chunks) ==="]
    for idx, d in enumerate(docs, start=1):
        m = d.metadata
        cid = m.get("chunk_id", "N/A")
        score_info = f"Score: {m.get('dense_score')}" if "dense_score" in m else f"Rank: {m.get('sparse_rank')}"
        bc = m.get("breadcrumbs", "")
        snippet = d.page_content[:140].replace("\n", " ").strip()
        lines.append(f"[{idx}] {cid} | {score_info} | {bc}")
        lines.append(f"    Snippet: \"{snippet}...\"\n")
    return "\n".join(lines)


# =====================================================================
# 5. DIAGNOSTIC / DEMO RUNNER
# =====================================================================

def demo_retrieval(query: str = "What are the rules and limits for domestic flight reimbursement?"):
    """Demonstrates standalone dense, sparse, and dual retrieval on a sample query."""
    print("=" * 80)
    print(f"QUERY: '{query}'")
    print("=" * 80)

    # 1. Dense alone
    dense_hits = retrieve_dense(query=query, k=3)
    print(format_retrieval_summary(dense_hits, mode_label="Dense Retrieval (Qdrant HNSW)"))

    # 2. Sparse alone
    sparse_hits = retrieve_sparse(query=query, k=3)
    print(format_retrieval_summary(sparse_hits, mode_label="Sparse Retrieval (BM25)"))

    # 3. Both ready for fusion
    candidates = retrieve_both(query=query, dense_k=3, sparse_k=3)
    print(f"\n[Ready for Fusion] {len(candidates['dense'])} Dense + {len(candidates['sparse'])} Sparse candidates retrieved.")
    print("=" * 80)


if __name__ == "__main__":
    demo_retrieval()
