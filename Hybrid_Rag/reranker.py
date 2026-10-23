"""Cohere Reranking Module for Hybrid RAG (Functional Approach).

Takes candidate chunks fused via Reciprocal Rank Fusion (RRF) and performs
cross-encoder neural reranking using Cohere Rerank v3.5 to determine the final
most relevant chunks for LLM context generation.

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

# Ensure local directories are in python path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
if str(CURRENT_DIR) in sys.path:
    sys.path.remove(str(CURRENT_DIR))
sys.path.insert(0, str(CURRENT_DIR))

from dotenv import load_dotenv
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

import cohere
from langchain_core.documents import Document

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("hybrid_rag.reranker")

DEFAULT_RERANK_MODEL = os.getenv("COHERE_RERANK_MODEL", "rerank-v3.5")


# =====================================================================
# 1. CLIENT INITIALIZATION
# =====================================================================

def get_cohere_client(api_key: Optional[str] = None) -> cohere.ClientV2:
    """Instantiates and returns a Cohere ClientV2 client.

    Args:
        api_key: Optional explicit API key. If omitted, reads COHERE_API_KEY from environment.

    Returns:
        cohere.ClientV2 instance.
    """
    key = api_key or os.getenv("COHERE_API_KEY")
    if not key or key == "your_cohere_api_key_here":
        raise ValueError(
            "COHERE_API_KEY is not set or invalid. Please check your .env configuration."
        )
    return cohere.ClientV2(api_key=key)


# =====================================================================
# 2. RERANKING FUNCTION
# =====================================================================

def rerank_chunks(
    query: str,
    documents: List[Document],
    top_n: int = 5,
    model: str = DEFAULT_RERANK_MODEL,
    client: Optional[cohere.ClientV2] = None,
    ) -> List[Document]:
    """Reranks candidate Document chunks using Cohere cross-encoder reranker.

    Takes fused candidates (e.g., from RRF), extracts their text payloads,
    submits them to Cohere's rerank endpoint, and returns the top_n most
    relevant chunks with full prior metadata and new rerank diagnostics attached.

    Args:
        query: The user search query.
        documents: List of candidate LangChain Document objects.
        top_n: Number of top reranked documents to return (default: 5).
        model: Cohere rerank model (default: 'rerank-v3.5').
        client: Optional pre-initialized cohere.ClientV2 instance.

    Returns:
        List of reranked LangChain Document objects sorted by relevance_score descending.
    """
    if not query.strip():
        logger.warning("Empty query passed to rerank_chunks.")
        return []

    if not documents:
        logger.warning("Empty document list passed to rerank_chunks.")
        return []

    start_time = time.time()
    co_client = client or get_cohere_client()

    # Extract text content from documents
    doc_texts = [doc.page_content for doc in documents]

    # Effective top_n cannot exceed number of candidates
    effective_top_n = min(top_n, len(documents))

    logger.info(
        f"[Cohere Rerank] Submitting {len(documents)} candidates to {model} "
        f"for query: '{query[:40]}' (target top_n: {effective_top_n})"
    )

    response = co_client.rerank(
        model=model,
        query=query,
        documents=doc_texts,
        top_n=effective_top_n,
    )

    reranked_docs: List[Document] = []
    for new_rank, item in enumerate(response.results, start=1):
        original_idx = item.index
        relevance_score = round(float(item.relevance_score), 6)
        original_doc = documents[original_idx]

        # Clone and enrich metadata with rerank provenance
        new_meta = dict(original_doc.metadata)
        prior_rrf_rank = new_meta.get("rrf_rank")

        new_meta.update({
            "rerank_rank": new_rank,
            "rerank_score": relevance_score,
            "rerank_model": model,
            "prior_rrf_rank": prior_rrf_rank,
            "rank_change": (prior_rrf_rank - new_rank) if prior_rrf_rank is not None else None,
        })

        reranked_docs.append(Document(page_content=original_doc.page_content, metadata=new_meta))

    latency_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(
        f"[Cohere Rerank] Completed reranking in {latency_ms} ms. Returned top {len(reranked_docs)} chunks."
    )
    return reranked_docs


# =====================================================================
# 3. FORMATTING & INSPECTION HELPERS
# =====================================================================

def format_rerank_table(
    initial_docs: List[Document],
    reranked_docs: List[Document],
    model: str = DEFAULT_RERANK_MODEL,
    ) -> str:
    """Formats a diagnostic table comparing pre-rerank (RRF) and post-rerank positions."""
    lines = []
    lines.append("=" * 115)
    lines.append(f"COHERE RERANKING RESULTS (Model: {model})")
    lines.append("=" * 115)
    lines.append(
        f"{'Rerank#':<8} | {'Chunk ID':<32} | {'Rerank Score':<12} | {'Prior RRF#':<10} | {'Shift':<10} | {'Sources'}"
    )
    lines.append("-" * 115)

    for doc in reranked_docs:
        m = doc.metadata
        r_rank = m.get("rerank_rank", "N/A")
        cid = m.get("chunk_id", "N/A")
        r_score = f"{m.get('rerank_score', 0.0):.6f}"
        rrf_rank = m.get("prior_rrf_rank", "N/A")
        
        shift_val = m.get("rank_change")
        if shift_val is not None:
            if shift_val > 0:
                shift_str = f"+{shift_val} [UP]"
            elif shift_val < 0:
                shift_str = f"{shift_val} [DOWN]"
            else:
                shift_str = "= [SAME]"
        else:
            shift_str = "--"

        sources = "+".join(m.get("retrieved_by", []))
        if m.get("in_both"):
            sources += " *[BOTH]"

        lines.append(
            f"#{r_rank:<7} | {cid:<32} | {r_score:<12} | #{rrf_rank:<9} | {shift_str:<10} | {sources}"
        )

    lines.append("-" * 115)
    lines.append(f"Filtered {len(initial_docs)} input candidate chunks -> Top {len(reranked_docs)} reranked chunks")
    lines.append("=" * 115)
    return "\n".join(lines)


# =====================================================================
# 4. STANDALONE DEMO
# =====================================================================

def demo_reranker():
    """Runs a standalone demonstration of reranking on dummy and real chunks."""
    from retriever import retrieve_hybrid_rrf

    sample_query = "What are the rules and limits for domestic flight reimbursement?"
    print(f"\n[Reranker Demo] Retrieving top 10 fused candidates for: '{sample_query}'...")
    candidates = retrieve_hybrid_rrf(query=sample_query, dense_k=10, sparse_k=10, top_n=10)

    print(f"\n[Reranker Demo] Reranking {len(candidates)} candidates down to Top 5 with Cohere rerank-v3.5...")
    top5_reranked = rerank_chunks(query=sample_query, documents=candidates, top_n=5)

    print("\n" + format_rerank_table(candidates, top5_reranked))


if __name__ == "__main__":
    demo_reranker()
