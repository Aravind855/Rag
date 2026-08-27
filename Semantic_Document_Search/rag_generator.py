"""
RAG Generator Module for NexaCore Semantic Document Search.

Integrates FAISS Retriever with Gemini LLM model to generate grounded answers
from retrieved document context.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Ensure parent directory is in path to import llm.py
sys.path.append(str(Path(__file__).resolve().parent.parent))
from llm import get_gemini_llm, get_llm
from document_embedder import DocumentEmbedder
from faiss_indexer import FAISSVectorIndex, SearchResult
from retriever import DocumentRetriever

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        load_dotenv(override=True)
except ImportError:
    pass

logger = logging.getLogger(__name__)

# RAG System Prompt Template
RAG_SYSTEM_PROMPT = """You are NexaCore Knowledge Assistant, a helpful AI specialized in answering employee and technical inquiries about NexaCore policies and guidelines.

Strict Guidelines:
1. Answer the user's question accurately using ONLY the provided document context below.
2. If the context does not contain enough information to answer the question, state: "I cannot find this information in the provided NexaCore documentation."
3. Keep your response professional, concise, clear, and well-structured (use bullet points or Markdown where helpful).
4. Always mention the source file name and page number if referenced in the context.

--- RETRIEVED DOCUMENT CONTEXT ---
{context}

--- USER QUESTION ---
{query}

--- ANSWER ---
"""


class NexaCoreRAGGenerator:
    """End-to-End RAG Generator combining semantic retriever with LLM response generation."""

    def __init__(
        self,
        vector_index: FAISSVectorIndex,
        embedder: DocumentEmbedder,
        provider: str = "gemini",
        model_name: Optional[str] = None,
        temperature: float = 0.2,
    ):
        self.retriever = DocumentRetriever(vector_index=vector_index, embedder=embedder)
        self.provider = provider.lower().strip()

        logger.info(f"Initializing LLM model (Provider: '{self.provider}')...")
        try:
            if self.provider == "gemini":
                self.llm = get_gemini_llm(temperature=temperature, model=model_name)
            else:
                self.llm = get_llm(provider=self.provider, temperature=temperature, model=model_name)
            logger.info("LLM initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize LLM ({self.provider}): {e}")
            raise e

    def generate_response(
        self,
        query: str,
        top_k: int = 3,
        category_filter: Optional[str] = None,
        print_context: bool = True,
    ) -> Dict[str, Any]:
        """Retrieve relevant context and generate LLM response.

        Args:
            query: Question text string.
            top_k: Number of chunks to retrieve.
            category_filter: Optional document category filter.
            print_context: If True, prints retrieved context snippets to stdout.

        Returns:
            Dictionary containing 'query', 'retrieved_results', 'context_text', and 'answer'.
        """
        # 1. Retrieve Context
        results = self.retriever.retrieve(query, top_k=top_k, category_filter=category_filter)
        context_text = self.retriever.format_retrieved_context(results)

        # 2. Optionally print retrieved context
        if print_context:
            print("\n" + "=" * 80)
            print(" 📌 RETRIEVED DOCUMENT CONTEXT")
            print("=" * 80)
            print(context_text)
            print("=" * 80)

        # 3. Construct Prompt & Generate Answer via LLM
        prompt = RAG_SYSTEM_PROMPT.format(context=context_text, query=query)
        logger.info("Sending query and retrieved context to LLM model...")

        response = self.llm.invoke(prompt)
        answer = response.content if hasattr(response, "content") else str(response)

        return {
            "query": query,
            "retrieved_results": results,
            "context_text": context_text,
            "answer": answer,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("NexaCoreRAGGenerator module ready.")
