"""Context Construction & LLM Response Generation Module for Hybrid RAG (Functional Approach).

Integrates Google Gemini (gemini-2.5-flash) with structured context construction
over top-5 Cohere reranked chunks. Produces factual, grounded answers with
transparent source citations and breadcrumb references.

All paths are resolved dynamically without hardcoding.
All operations are written as pure procedural functions without classes.
"""

import logging
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

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

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from reranker import rerank_chunks
from retriever import retrieve_hybrid_rrf

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("hybrid_rag.generator")

DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DEFAULT_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))


# =====================================================================
# 1. LLM CLIENT INITIALIZATION
# =====================================================================

def get_gemini_llm(
    model: str = DEFAULT_GEMINI_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    api_key: Optional[str] = None,
    ) -> ChatGoogleGenerativeAI:
    """Instantiates and returns the configured ChatGoogleGenerativeAI instance.

    Args:
        model: Google Gemini model identifier (default: 'gemini-2.5-flash').
        temperature: Sampling temperature for generation (default: 0.2 for factual answers).
        api_key: Optional explicit API key. Defaults to GEMINI_API_KEY / GOOGLE_API_KEY.

    Returns:
        ChatGoogleGenerativeAI client.
    """
    key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key or key == "your_gemini_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY or GOOGLE_API_KEY is not configured in .env."
        )

    try:
        llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=key,
            temperature=temperature,
        )
        return llm
    except Exception as e:
        logger.warning(f"Failed to initialize model '{model}': {e}. Falling back to 'gemini-1.5-flash'...")
        return ChatGoogleGenerativeAI(
            model="gemini-3.5-flash-lite",
            google_api_key=key,
            temperature=temperature,
        )


# =====================================================================
# 2. STRUCTURED CONTEXT CONSTRUCTION
# =====================================================================

def build_context(documents: Sequence[Document]) -> Tuple[str, List[Dict[str, Any]]]:
    """Constructs a structured, citation-friendly context block from reranked chunks.

    Formats each document with explicit chunk boundaries, source numbering,
    hierarchical breadcrumbs, and provenance metadata so the LLM can generate
    verifiable, grounded citations.

    Args:
        documents: List of reranked LangChain Document objects.

    Returns:
        Tuple containing:
        - formatted_context_str: Clean text block ready for prompt injection.
        - sources_metadata: List of dicts describing each source for output verification.
    """
    if not documents:
        return "No relevant context documents found.", []

    context_segments = []
    sources_metadata: List[Dict[str, Any]] = []

    for idx, doc in enumerate(documents, start=1):
        m = doc.metadata
        chunk_id = m.get("chunk_id", f"chunk_{idx}")
        category = m.get("category", "General")
        doc_type = m.get("document_type", "Document")
        breadcrumbs = m.get("breadcrumbs", "")
        file_name = m.get("file_name", m.get("source", ""))
        rerank_score = m.get("rerank_score", "N/A")

        # Source reference record for downstream citation tracking
        source_info = {
            "source_index": idx,
            "chunk_id": chunk_id,
            "category": category,
            "document_type": doc_type,
            "file_name": file_name,
            "breadcrumbs": breadcrumbs,
            "rerank_score": rerank_score,
            "snippet": doc.page_content[:160].replace("\n", " ").strip(),
        }
        sources_metadata.append(source_info)

        # Build clean chunk block with clear delimitation
        header_parts = [f"Source [{idx}] (ID: {chunk_id})"]
        if breadcrumbs:
            header_parts.append(f"Section: {breadcrumbs}")
        elif file_name:
            header_parts.append(f"File: {file_name}")

        header_line = " | ".join(header_parts)
        cleaned_content = doc.page_content.strip()

        segment = (
            f"--- BEGIN SOURCE [{idx}] ---\n"
            f"Reference: {header_line}\n"
            f"Content:\n{cleaned_content}\n"
            f"--- END SOURCE [{idx}] ---"
        )
        context_segments.append(segment)

    formatted_context_str = "\n\n".join(context_segments)
    return formatted_context_str, sources_metadata


# =====================================================================
# 3. PROMPT TEMPLATING
# =====================================================================

SYSTEM_RAG_PROMPT = """You are an expert enterprise AI assistant for NexaCore internal documentation.
    Your mission is to answer employee and stakeholder questions accurately, concisely, and factually, strictly relying on the provided context.

    Guidelines:
    1. STRICT GROUNDING: Answer ONLY using information explicitly stated in the provided context sources. Do not speculate or invent facts.
    2. CITATIONS: Every key claim, policy limit, rule, or procedure must be cited with its corresponding source bracket, e.g., [Source 1], [Source 2].
    3. COMPLETENESS: If the query asks for specific numbers, conditions, exception owners, or steps, detail them clearly using bullet points or concise tables.
    4. HONEST UNCERTAINTY: If the provided context does not contain enough information to answer the question, clearly state: "The provided internal documentation does not contain information regarding [specific missing detail]."
    5. TONE: Professional, authoritative, and direct. Avoid conversational filler like "Based on the provided documents".
    """


def build_rag_prompt(query: str, context: str) -> List[Union[SystemMessage, HumanMessage]]:
    """Constructs the LangChain chat messages for LLM invocation."""
    user_message_content = f"""QUESTION:
    {query.strip()}

    RETRIEVED DOCUMENTATION CONTEXT:
    {context}

    Please provide a clear, factual answer with exact citations [Source X] for every claim made."""

    return [
        SystemMessage(content=SYSTEM_RAG_PROMPT),
        HumanMessage(content=user_message_content),
    ]


# =====================================================================
# 4. LLM GENERATION FUNCTION
# =====================================================================

def generate_rag_answer(
    query: str,
    documents: List[Document],
    model: str = DEFAULT_GEMINI_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    llm: Optional[ChatGoogleGenerativeAI] = None,
    ) -> Dict[str, Any]:
    """Builds context from reranked documents and executes LLM generation using Google Gemini.

    Args:
        query: User search query.
        documents: List of top reranked Document chunks.
        model: Target Gemini model name.
        temperature: Generation temperature (lower = more factual).
        llm: Optional pre-configured ChatGoogleGenerativeAI client.

    Returns:
        Dictionary containing:
        {
            "query": str,
            "answer": str,
            "sources": List[Dict[str, Any]],
            "context": str,
            "generation_time_ms": float,
            "model": str,
        }
    """
    start_time = time.time()
    active_llm = llm or get_gemini_llm(model=model, temperature=temperature)

    # 1. Build structured context and source citations
    context_str, sources_metadata = build_context(documents)

    # 2. Build prompt messages
    messages = build_rag_prompt(query=query, context=context_str)

    # 3. Invoke LLM
    logger.info(f"[LLM Generation] Invoking {model} for query: '{query[:40]}' with {len(documents)} context chunks...")
    response = active_llm.invoke(messages)

    # Robust extraction of string content whether returned as str or list of block dicts
    if isinstance(response.content, str):
        answer_text = response.content
    elif isinstance(response.content, list):
        text_parts = []
        for block in response.content:
            if isinstance(block, dict) and "text" in block:
                text_parts.append(block["text"])
            elif isinstance(block, str):
                text_parts.append(block)
        answer_text = "\n".join(text_parts) if text_parts else str(response.content)
    else:
        answer_text = str(response.content)

    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(f"[LLM Generation] Response generated in {elapsed_ms} ms.")

    return {
        "query": query,
        "answer": answer_text.strip(),
        "sources": sources_metadata,
        "context": context_str,
        "generation_time_ms": elapsed_ms,
        "model": model,
    }


# =====================================================================
# 5. FULL END-TO-END HYBRID RAG PIPELINE
# =====================================================================

def run_hybrid_rag(
    query: str,
    dense_k: int = 10,
    sparse_k: int = 10,
    rrf_top_n: int = 10,
    rerank_top_n: int = 5,
    rrf_k: int = 60,
    llm_model: str = DEFAULT_GEMINI_MODEL,
    llm_temperature: float = DEFAULT_TEMPERATURE,
    ) -> Dict[str, Any]:
    """Complete end-to-end procedural Hybrid RAG Pipeline:

    1. DUAL RETRIEVAL: 10 Dense (Qdrant HNSW) + 10 Sparse (BM25)
    2. RECIPROCAL RANK FUSION: Fuses candidate streams into top 10 unique chunks
    3. NEURAL RERANKING: Cohere rerank-v3.5 reranks candidates down to Top 5
    4. CONTEXT CONSTRUCTION: Builds structured context with breadcrumb provenance
    5. SYNTHESIS: Google Gemini (gemini-2.5-flash) generates factual answer with citations

    Args:
        query: User input question.
        dense_k: Dense candidates to fetch (default: 10).
        sparse_k: Sparse candidates to fetch (default: 10).
        rrf_top_n: Fused candidates before reranking (default: 10).
        rerank_top_n: Final chunks passed to context (default: 5).
        rrf_k: RRF smoothing constant (default: 60).
        llm_model: Gemini model identifier (default: 'gemini-2.5-flash').
        llm_temperature: LLM temperature (default: 0.2).

    Returns:
        Comprehensive pipeline results dictionary with query, answer, sources, and timings.
    """
    total_start = time.time()
    logger.info(f"=== Starting Hybrid RAG Pipeline for query: '{query}' ===")

    # Step 1 & 2 & 3: Dual Retrieval + Reciprocal Rank Fusion
    t_retrieval_start = time.time()
    fused_candidates = retrieve_hybrid_rrf(
        query=query,
        dense_k=dense_k,
        sparse_k=sparse_k,
        top_n=rrf_top_n,
        rrf_k=rrf_k,
    )
    retrieval_ms = round((time.time() - t_retrieval_start) * 1000, 2)

    # Step 4: Neural Reranking via Cohere
    t_rerank_start = time.time()
    reranked_chunks = rerank_chunks(
        query=query,
        documents=fused_candidates,
        top_n=rerank_top_n,
    )
    rerank_ms = round((time.time() - t_rerank_start) * 1000, 2)

    # Step 5 & 6: Context Construction + LLM Synthesis via Google Gemini
    t_gen_start = time.time()
    generation_result = generate_rag_answer(
        query=query,
        documents=reranked_chunks,
        model=llm_model,
        temperature=llm_temperature,
    )
    generation_ms = round((time.time() - t_gen_start) * 1000, 2)

    total_latency_ms = round((time.time() - total_start) * 1000, 2)

    return {
        "query": query,
        "answer": generation_result["answer"],
        "sources": generation_result["sources"],
        "context": generation_result["context"],
        "reranked_documents": reranked_chunks,
        "fused_documents": fused_candidates,
        "timings": {
            "retrieval_and_fusion_ms": retrieval_ms,
            "rerank_ms": rerank_ms,
            "generation_ms": generation_ms,
            "total_pipeline_ms": total_latency_ms,
        },
        "model": llm_model,
    }


# =====================================================================
# 6. DEMO & INTERACTIVE CLI RUNNER
# =====================================================================

def demo_hybrid_rag(query: str = "What are the rules and limits for domestic flight reimbursement?"):
    """Runs a complete end-to-end demonstration and prints the full lifecycle."""
    print("\n" + "=" * 115)
    print("HYBRID RAG PIPELINE: END-TO-END DEMONSTRATION")
    print(f"QUERY: \"{query}\"")
    print("=" * 115)

    result = run_hybrid_rag(query=query)

    print("\n" + "-" * 115)
    print("STAGE 1: TOP 5 RERANKED CONTEXT SOURCES (Cohere rerank-v3.5)")
    print("-" * 115)
    for src in result["sources"]:
        idx = src["source_index"]
        cid = src["chunk_id"]
        score = src["rerank_score"]
        bc = src["breadcrumbs"]
        print(f"[{idx}] {cid:<34} | Rerank Score: {score} | Section: {bc}")
        print(f"    Snippet: \"{src['snippet']}...\"\n")

    print("-" * 115)
    print(f"STAGE 2: GENERATED ANSWER (Google Gemini: {result['model']})")
    print("-" * 115)
    print(result["answer"])

    print("\n" + "-" * 115)
    print("STAGE 3: PIPELINE LATENCY TELEMETRY")
    print("-" * 115)
    t = result["timings"]
    print(f" - Dual Retrieval + RRF Fusion: {t['retrieval_and_fusion_ms']} ms")
    print(f" - Cohere Neural Reranking:    {t['rerank_ms']} ms")
    print(f" - Context Build + Gemini Gen:  {t['generation_ms']} ms")
    print(f" - TOTAL PIPELINE LATENCY:      {t['total_pipeline_ms']} ms")
    print("=" * 115 + "\n")
    return result


def interactive_hybrid_rag():
    """Interactive CLI runner allowing the user to enter custom queries in a loop or via CLI arguments."""
    # 1. Check if query was passed as command-line arguments: python generator.py "my query"
    if len(sys.argv) > 1 and sys.argv[1].strip():
        cli_query = " ".join(sys.argv[1:]).strip()
        demo_hybrid_rag(query=cli_query)
        return

    # 2. Interactive prompt loop
    print("\n" + "=" * 115)
    print("NEXACORE HYBRID RAG ASSISTANT (Qdrant + BM25 + RRF + Cohere Rerank + Google Gemini)")
    print("Type your question below and press [Enter].")
    print("Commands:")
    print(" - Press [Enter] with empty prompt to run the default sample query.")
    print(" - Type 'q', 'quit', or 'exit' to terminate the session.")
    print("=" * 115)

    default_sample = "What are the rules and limits for domestic flight reimbursement?"

    while True:
        try:
            prompt_label = f"\n[?] Enter your query (press Enter for default '{default_sample[:40]}...'):\n>>> "
            user_input = input(prompt_label).strip()

            if user_input.lower() in ("q", "quit", "exit"):
                print("\n[+] Exiting NexaCore Hybrid RAG Assistant. Have a great day!\n")
                break

            query = user_input if user_input else default_sample
            demo_hybrid_rag(query=query)

        except (KeyboardInterrupt, EOFError):
            print("\n\n[+] Session interrupted. Exiting...\n")
            break


if __name__ == "__main__":
    interactive_hybrid_rag()
