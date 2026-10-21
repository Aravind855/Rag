"""Hybrid Retrieval and Fusion Module for Hybrid RAG (Functional Approach).

Implements independent dense and sparse retrieval strategies plus Reciprocal Rank Fusion (RRF):
1. Dense Retrieval: Cohere query embeddings (embed-v5.0-fast) + Qdrant HNSW graph search (10 candidates).
2. Sparse Retrieval: Domain-aware tokenization + BM25 inverted index search (10 candidates).
3. Dual Candidate Retrieval: Fetches 10 dense + 10 sparse candidate pools.
4. Reciprocal Rank Fusion (RRF): Deduplicates and fuses candidates using standard RRF (k=60),
   boosting cross-modal consensus documents into the top-10 fused ranking.

All paths are resolved dynamically without hardcoding.
All operations are written as pure procedural functions without classes.
"""

import logging
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Union

# Configure stdout and stderr to UTF-8 with replace fallback for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv

# Ensure local Hybrid_Rag directory is strictly at index 0 for module resolution
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
if str(CURRENT_DIR) in sys.path:
    sys.path.remove(str(CURRENT_DIR))
sys.path.insert(0, str(CURRENT_DIR))

from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.http.models import SearchParams

# Functional imports from local modules
try:
    from bm25_indexer import custom_bm25_tokenizer, load_bm25_retriever
    from embeddings import embed_query_text, get_cohere_embeddings
    from qdrant_indexer import (
        DEFAULT_COLLECTION_NAME,
        get_qdrant_client,
        get_qdrant_retriever,
    )
except ImportError:
    from Hybrid_Rag.bm25_indexer import custom_bm25_tokenizer, load_bm25_retriever
    from Hybrid_Rag.embeddings import embed_query_text, get_cohere_embeddings
    from Hybrid_Rag.qdrant_indexer import (
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
    k: int = 10,
    hnsw_ef: int = 64,
    client: Optional[QdrantClient] = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    ) -> List[Document]:
    """Retrieves top-k semantically similar chunks from Qdrant using Cohere embeddings.

    Executes HNSW approximate nearest neighbor search via Qdrant's graph index.

    Args:
        query: User search query.
        k: Number of top documents to retrieve (default: 10).
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
    k: int = 10,
    index_path: Optional[Union[str, Path]] = None,
    retriever: Optional[BM25Retriever] = None,
    ) -> List[Document]:
    """Retrieves top-k lexically matching chunks from the BM25 inverted index.

    Tokenizes query with custom domain-aware tokenizer to preserve exact
    technical IDs (SYS-001, TRV-AIR), codes, numbers, and currencies.

    Args:
        query: User search query.
        k: Number of top documents to retrieve (default: 10).
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
# 3. DUAL RETRIEVAL (10 DENSE + 10 SPARSE CANDIDATE POOLS)
# =====================================================================

def retrieve_both(
    query: str,
    dense_k: int = 10,
    sparse_k: int = 10,
    hnsw_ef: int = 64,
    qdrant_client: Optional[QdrantClient] = None,
    bm25_retriever: Optional[BM25Retriever] = None,
    ) -> Dict[str, List[Document]]:
    """Executes both dense and sparse retrieval in parallel or sequence,

    fetching candidate pools (10 dense + 10 sparse by default) ready for fusion.

    Args:
        query: User search query.
        dense_k: Number of dense candidates to retrieve (default: 10).
        sparse_k: Number of sparse candidates to retrieve (default: 10).
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
        f"[Dual Retrieval] Fetched {len(dense_candidates)} dense + {len(sparse_candidates)} sparse "
        f"candidates in {total_latency_ms} ms"
    )

    return {
        "dense": dense_candidates,
        "sparse": sparse_candidates,
    }


# =====================================================================
# 4. RECIPROCAL RANK FUSION (RRF) MECHANISM
# =====================================================================

def reciprocal_rank_fusion(
    ranked_lists: Dict[str, List[Document]],
    rrf_k: int = 60,
    top_n: int = 10,
    weights: Optional[Dict[str, float]] = None,
    ) -> List[Document]:
    """Combines multiple ranked document lists into a single fused ranking using RRF.

    Reciprocal Rank Fusion formula:
        RRF_Score(d) = SUM_{m in M} ( w_m / (rrf_k + rank_m(d)) )

    where:
    - m is the retrieval modality (e.g. 'dense', 'sparse')
    - rank_m(d) is the 1-based position of document d in list m
    - rrf_k is the standard smoothing constant (default: 60)
    - w_m is an optional modality weight (default: 1.0 for each)

    Documents retrieved across multiple streams naturally receive a score boost,
    promoting high-confidence cross-modal consensus.

    Args:
        ranked_lists: Dict mapping stream name to ranked Document list,
                      e.g. {"dense": [...], "sparse": [...]}.
        rrf_k: Rank smoothing constant (default: 60, standard IR benchmark).
        top_n: Number of fused documents to return (default: 10).
        weights: Optional weights per modality, e.g. {"dense": 1.0, "sparse": 1.0}.

    Returns:
        Deduplicated and reranked list of LangChain Document objects with
        fused RRF metadata.
    """
    if not ranked_lists:
        return []

    scores: Dict[str, float] = {}
    doc_registry: Dict[str, Document] = {}
    doc_provenance: Dict[str, Dict[str, Any]] = {}

    for modality, docs in ranked_lists.items():
        weight = weights.get(modality, 1.0) if weights else 1.0

        for rank, doc in enumerate(docs, start=1):
            # Unique identifier: chunk_id preferred, fallback to content hash
            chunk_id = doc.metadata.get("chunk_id")
            if not chunk_id:
                chunk_id = f"content_{abs(hash(doc.page_content.strip()[:120]))}"

            # Calculate RRF score contribution: w / (k + rank)
            contribution = weight / (rrf_k + rank)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + contribution

            # Register document instance
            if chunk_id not in doc_registry:
                doc_registry[chunk_id] = doc
                doc_provenance[chunk_id] = {
                    "sources": [],
                    "dense_rank": None,
                    "sparse_rank": None,
                    "dense_score": doc.metadata.get("dense_score"),
                    "contributions": {},
                }

            prov = doc_provenance[chunk_id]
            if modality not in prov["sources"]:
                prov["sources"].append(modality)
            prov["contributions"][modality] = round(contribution, 6)

            if modality == "dense":
                prov["dense_rank"] = rank
                if "dense_score" in doc.metadata:
                    prov["dense_score"] = doc.metadata["dense_score"]
            elif modality == "sparse":
                prov["sparse_rank"] = rank

    # Sort documents by descending RRF score
    sorted_chunk_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)
    fused_chunk_ids = sorted_chunk_ids[:top_n]

    fused_docs: List[Document] = []
    for final_rank, cid in enumerate(fused_chunk_ids, start=1):
        base_doc = doc_registry[cid]
        prov = doc_provenance[cid]
        final_score = scores[cid]

        # Construct comprehensive diagnostic metadata
        merged_meta = dict(base_doc.metadata)
        merged_meta.update({
            "chunk_id": cid,
            "retrieval_mode": "hybrid_rrf",
            "rrf_rank": final_rank,
            "rrf_score": round(final_score, 6),
            "dense_rank": prov["dense_rank"],
            "sparse_rank": prov["sparse_rank"],
            "dense_score": prov["dense_score"],
            "retrieved_by": prov["sources"],
            "in_both": len(prov["sources"]) > 1,
            "rrf_k": rrf_k,
            "rrf_contributions": prov["contributions"],
        })

        fused_docs.append(Document(page_content=base_doc.page_content, metadata=merged_meta))

    logger.info(
        f"[RRF Fusion] Fused {len(sorted_chunk_ids)} unique candidates from "
        f"{list(ranked_lists.keys())} -> returning top {len(fused_docs)} documents."
    )
    return fused_docs


def retrieve_hybrid_rrf(
    query: str,
    dense_k: int = 10,
    sparse_k: int = 10,
    top_n: int = 10,
    rrf_k: int = 60,
    weights: Optional[Dict[str, float]] = None,
    hnsw_ef: int = 64,
    qdrant_client: Optional[QdrantClient] = None,
    bm25_retriever: Optional[BM25Retriever] = None,
    ) -> List[Document]:
    """Retrieves 10 dense and 10 sparse candidates and fuses them using Reciprocal Rank Fusion.

    Complete end-to-end procedural Hybrid RAG retriever:
    1. Fetches top `dense_k` (10) candidates from Qdrant HNSW via Cohere embeddings.
    2. Fetches top `sparse_k` (10) candidates from BM25 using domain-aware tokenizer.
    3. Fuses both ranked streams with Reciprocal Rank Fusion (k=60).
    4. Returns deduplicated, boosted top `top_n` (10) chunks.

    Args:
        query: User search query.
        dense_k: Number of candidates from dense vector search (default: 10).
        sparse_k: Number of candidates from sparse BM25 search (default: 10).
        top_n: Final number of fused documents to return (default: 10).
        rrf_k: RRF smoothing constant (default: 60).
        weights: Optional stream weights (e.g. {"dense": 1.0, "sparse": 1.0}).
        hnsw_ef: Qdrant HNSW search beam width (default: 64).
        qdrant_client: Optional QdrantClient instance.
        bm25_retriever: Optional BM25Retriever instance.

    Returns:
        List of top_n hybrid documents ranked by reciprocal rank fusion.
    """
    start_time = time.time()

    # 1. Fetch candidates from both streams (10 dense + 10 sparse)
    candidates = retrieve_both(
        query=query,
        dense_k=dense_k,
        sparse_k=sparse_k,
        hnsw_ef=hnsw_ef,
        qdrant_client=qdrant_client,
        bm25_retriever=bm25_retriever,
    )

    # 2. Fuse candidate pools using Reciprocal Rank Fusion
    fused_results = reciprocal_rank_fusion(
        ranked_lists=candidates,
        rrf_k=rrf_k,
        top_n=top_n,
        weights=weights,
    )

    latency_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(
        f"[Hybrid RRF Retrieval] Completed in {latency_ms} ms. Returned {len(fused_results)} chunks for query: '{query[:40]}'"
    )
    return fused_results


# =====================================================================
# 5. INSPECTION & FORMATTING HELPERS
# =====================================================================

def format_retrieval_summary(docs: Sequence[Document], mode_label: str = "Results") -> str:
    """Formats retrieved Document chunks into a readable summary table/list."""
    lines = [f"\n=== {mode_label.upper()} ({len(docs)} chunks) ==="]
    for idx, d in enumerate(docs, start=1):
        m = d.metadata
        cid = m.get("chunk_id", "N/A")

        score_parts = []
        if "rrf_score" in m:
            score_parts.append(f"RRF: {m.get('rrf_score'):.6f}")
            sources = "+".join(m.get("retrieved_by", []))
            both_flag = " ⭐ [IN BOTH]" if m.get("in_both") else ""
            score_parts.append(f"Sources: [{sources}]{both_flag}")
            if m.get("dense_rank") is not None:
                score_parts.append(f"D-Rank: #{m.get('dense_rank')}")
            if m.get("sparse_rank") is not None:
                score_parts.append(f"S-Rank: #{m.get('sparse_rank')}")
        elif "dense_score" in m:
            score_parts.append(f"Score: {m.get('dense_score')}")
        elif "sparse_rank" in m:
            score_parts.append(f"Rank: #{m.get('sparse_rank')}")

        score_info = " | ".join(score_parts)
        bc = m.get("breadcrumbs", "")
        raw_snip = d.page_content[:140].replace("\n", " ").strip()
        snippet = raw_snip.encode("ascii", errors="replace").decode("ascii")
        lines.append(f"[{idx:02d}] {cid:<32} | {score_info} | {bc}")
        lines.append(f"     Snippet: \"{snippet}...\"\n")
    return "\n".join(lines)


def format_fusion_explanation_table(
    dense_docs: List[Document],
    sparse_docs: List[Document],
    fused_docs: List[Document],
    rrf_k: int = 60,
    ) -> str:
    """Generates a detailed mathematical explanation table of how RRF scored every candidate."""
    dense_ranks = {d.metadata.get("chunk_id"): (idx + 1, d.metadata.get("dense_score")) for idx, d in enumerate(dense_docs)}
    sparse_ranks = {d.metadata.get("chunk_id"): idx + 1 for idx, d in enumerate(sparse_docs)}
    
    all_chunk_ids = list(dict.fromkeys(list(dense_ranks.keys()) + list(sparse_ranks.keys())))
    
    lines = []
    lines.append("=" * 110)
    lines.append(f"STEP 3: RECIPROCAL RANK FUSION (RRF) MATHEMATICAL BREAKDOWN (k = {rrf_k})")
    lines.append("Formula: RRF_Score(d) = SUM [ 1.0 / (k + rank(d)) ]")
    lines.append("=" * 110)
    lines.append(
        f"{'RRF#':<5} | {'Chunk ID':<32} | {'Dense Rank & Contrib':<26} | {'Sparse Rank & Contrib':<26} | {'RRF Score':<10} | {'Status'}"
    )
    lines.append("-" * 110)

    for final_rank, doc in enumerate(fused_docs, start=1):
        cid = doc.metadata.get("chunk_id", "N/A")
        m = doc.metadata
        
        # Dense contribution
        d_rank = m.get("dense_rank")
        if d_rank is not None:
            d_contrib = 1.0 / (rrf_k + d_rank)
            d_str = f"#{d_rank:<2} (1/{rrf_k}+{d_rank} = {d_contrib:.6f})"
        else:
            d_str = f"{'-- (not in top-10)':<26}"

        # Sparse contribution
        s_rank = m.get("sparse_rank")
        if s_rank is not None:
            s_contrib = 1.0 / (rrf_k + s_rank)
            s_str = f"#{s_rank:<2} (1/{rrf_k}+{s_rank} = {s_contrib:.6f})"
        else:
            s_str = f"{'-- (not in top-10)':<26}"

        rrf_sc = m.get("rrf_score", 0.0)
        status = "* [IN BOTH - BOOSTED]" if m.get("in_both") else f"[{'+'.join(m.get('retrieved_by', []))} only]"

        lines.append(
            f"#{final_rank:<4} | {cid:<32} | {d_str:<26} | {s_str:<26} | {rrf_sc:<10.6f} | {status}"
        )

    lines.append("-" * 110)
    
    both_count = sum(1 for d in fused_docs if d.metadata.get("in_both"))
    lines.append(f"Total Unique Candidates Evaluated: {len(all_chunk_ids)} (from 10 Dense + 10 Sparse)")
    lines.append(f"Candidates with Cross-Modal Consensus: {both_count} (boosted by combined reciprocal scores)")
    lines.append("=" * 110)
    return "\n".join(lines)


# =====================================================================
# 6. STEP-BY-STEP EXPLANATORY RETRIEVAL PIPELINE
# =====================================================================

def explain_retrieval_step_by_step(
    query: str = "What are the rules and limits for domestic flight reimbursement?",
    dense_k: int = 10,
    sparse_k: int = 10,
    top_n: int = 10,
    rrf_k: int = 60,
    ):
    """Executes the full hybrid retrieval pipeline with comprehensive step-by-step explanations:

    1. STEP 1: Dense Semantic Retrieval (Cohere + Qdrant HNSW)
    2. STEP 2: Sparse Keyword Retrieval (Domain BM25 Inverted Index)
    3. STEP 3: Reciprocal Rank Fusion (Detailed math and rank contribution table)
    4. STEP 4: Final Top-10 Fused Chunks (With complete provenance and snippets)
    """
    print("\n" + "#" * 110)
    print(f"HYBRID RETRIEVAL & FUSION DETAILED STEP-BY-STEP PIPELINE")
    print(f"QUERY: \"{query}\"")
    print("#" * 110)

    # -----------------------------------------------------------------
    # STEP 1: DENSE RETRIEVAL (SEMANTIC VECTOR SEARCH)
    # -----------------------------------------------------------------
    print("\n" + "=" * 110)
    print("STEP 1: DENSE RETRIEVAL (Cohere embed-v5.0-fast 2048-dim + Qdrant HNSW Graph Index)")
    print("How it works:")
    print(" - Converts user query into a 2048-dimensional dense vector.")
    print(" - Navigates the HNSW graph on Qdrant Cloud using Cosine Similarity.")
    print(f" - Retrieves the top {dense_k} most semantically relevant chunks regardless of exact keyword overlap.")
    print("=" * 110)

    dense_hits = retrieve_dense(query=query, k=dense_k)
    for idx, doc in enumerate(dense_hits, start=1):
        m = doc.metadata
        cid = m.get("chunk_id", "N/A")
        score = m.get("dense_score", "N/A")
        bc = m.get("breadcrumbs", "N/A")
        raw_snip = doc.page_content[:150].replace("\n", " ").strip()
        snippet = raw_snip.encode("ascii", errors="replace").decode("ascii")
        print(f" [Dense #{idx:02d}] {cid:<32} | Cosine Score: {score} | Breadcrumbs: {bc}")
        print(f"            Snippet: \"{snippet}...\"\n")

    # -----------------------------------------------------------------
    # STEP 2: SPARSE RETRIEVAL (LEXICAL KEYWORD SEARCH)
    # -----------------------------------------------------------------
    print("=" * 110)
    print("STEP 2: SPARSE RETRIEVAL (Domain-Aware BM25 Inverted Index)")
    print("How it works:")
    tokens = custom_bm25_tokenizer(query)
    print(f" - Tokenizes query with custom tokenizer: {tokens}")
    print(" - Preserves entity IDs, numbers, codes, and exact technical terminology.")
    print(f" - Computes BM25 TF-IDF relevance and retrieves the top {sparse_k} lexical candidates.")
    print("=" * 110)

    sparse_hits = retrieve_sparse(query=query, k=sparse_k)
    for idx, doc in enumerate(sparse_hits, start=1):
        m = doc.metadata
        cid = m.get("chunk_id", "N/A")
        bc = m.get("breadcrumbs", "N/A")
        raw_snip = doc.page_content[:150].replace("\n", " ").strip()
        snippet = raw_snip.encode("ascii", errors="replace").decode("ascii")
        print(f" [Sparse #{idx:02d}] {cid:<32} | BM25 Rank: #{idx} | Breadcrumbs: {bc}")
        print(f"             Snippet: \"{snippet}...\"\n")

    # -----------------------------------------------------------------
    # STEP 3: RECIPROCAL RANK FUSION (RRF) MATHEMATICAL BREAKDOWN
    # -----------------------------------------------------------------
    candidates = {"dense": dense_hits, "sparse": sparse_hits}
    fused_hits = reciprocal_rank_fusion(candidates, rrf_k=rrf_k, top_n=top_n)

    print(format_fusion_explanation_table(
        dense_docs=dense_hits,
        sparse_docs=sparse_hits,
        fused_docs=fused_hits,
        rrf_k=rrf_k,
    ))

    # -----------------------------------------------------------------
    # STEP 4: FINAL TOP-10 FUSED SELECTION FOR RAG
    # -----------------------------------------------------------------
    print("\n" + "=" * 110)
    print(f"STEP 4: FINAL TOP {top_n} FUSED CHUNKS (Supplied to LLM for Answer Generation)")
    print("Why this order matters:")
    print(" - Candidates verified by BOTH systems are elevated to the very top due to dual reciprocal bonuses.")
    print(" - Dense-only hits preserve deep semantic relevance even if phrasing differed.")
    print(" - Sparse-only hits preserve precise entity/ID matches that vector search might smooth over.")
    print("=" * 110)

    for rank, doc in enumerate(fused_hits, start=1):
        m = doc.metadata
        cid = m.get("chunk_id", "N/A")
        rrf_sc = m.get("rrf_score", 0.0)
        sources = "+".join(m.get("retrieved_by", []))
        both_tag = "* [CROSS-MODAL CONSENSUS]" if m.get("in_both") else f"[{sources} only]"
        d_rank_str = f"Dense Rank: #{m.get('dense_rank')}" if m.get("dense_rank") is not None else "Dense: not in top-10"
        s_rank_str = f"Sparse Rank: #{m.get('sparse_rank')}" if m.get("sparse_rank") is not None else "Sparse: not in top-10"
        bc = m.get("breadcrumbs", "N/A")
        raw_snip = doc.page_content[:180].replace("\n", " ").strip()
        snippet = raw_snip.encode("ascii", errors="replace").decode("ascii")

        print(f"[FINAL RANK #{rank:02d}] {cid} | RRF Score: {rrf_sc:.6f} | {both_tag}")
        print(f"  Provenance: {d_rank_str} | {s_rank_str}")
        print(f"  Hierarchy:  {bc}")
        print(f"  Excerpt:    \"{snippet}...\"\n")

    print("#" * 110 + "\n")
    return fused_hits


def demo_retrieval(query: str = "What are the rules and limits for domestic flight reimbursement?"):
    """Demonstrates detailed step-by-step hybrid retrieval and fusion on a sample query."""
    explain_retrieval_step_by_step(query=query, dense_k=10, sparse_k=10, top_n=10, rrf_k=60)


if __name__ == "__main__":
    demo_retrieval()



