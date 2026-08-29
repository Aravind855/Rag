"""
Query & RAG Response Runner for NexaCore Semantic Document Search.

Standalone query flow that loads the persisted FAISS vector index from disk,
retrieves document context, prints context snippets, and generates Gemini LLM answers.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Union

# Force UTF-8 encoding on standard output for Windows console compatibility
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        pass

# Ensure parent directory is in path to import llm.py and embeddings.py
sys.path.append(str(Path(__file__).resolve().parent.parent))

from document_embedder import DocumentEmbedder
from faiss_indexer import FAISSVectorIndex
from rag_generator import NexaCoreRAGGenerator

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("QueryRunner")


DEFAULT_INDEX_DIR = Path(__file__).resolve().parent.parent / "faiss_index"


class NexaCoreRAGQueryEngine:
    """Standalone Query Engine that loads FAISS index from disk and answers questions via LLM."""

    def __init__(
        self,
        index_dir: Optional[Union[str, Path]] = None,
        provider: str = "gemini",
        temperature: float = 0.2,
    ):
        target_dir = index_dir if index_dir is not None else DEFAULT_INDEX_DIR
        path = Path(target_dir).resolve()
        if not (path / "index.faiss").exists():
            logger.info(f"FAISS index not found at '{path}'. Running ingestion pipeline first...")
            from pipeline_runner import run_indexing_pipeline
            run_indexing_pipeline(output_dir=str(path))

        logger.info(f"Loading FAISS Vector Index from '{path}'...")
        self.vector_index = FAISSVectorIndex.load(path)
        self.embedder = DocumentEmbedder()
        self.rag_generator = NexaCoreRAGGenerator(
            vector_index=self.vector_index,
            embedder=self.embedder,
            provider=provider,
            temperature=temperature,
        )

    def query(self, question: str, top_k: int = 3, category_filter: Optional[str] = None) -> str:
        """Process user question: Retrieve context, print context snippets, and return LLM answer."""
        print("\n" + "#" * 80)
        print(f" ❓ USER QUESTION: '{question}'")
        print("#" * 80)

        # Generate response (automatically prints retrieved document context)
        output = self.rag_generator.generate_response(
            query=question,
            top_k=top_k,
            category_filter=category_filter,
            print_context=True,
        )

        print("\n" + "=" * 80)
        print(" 🤖 GEMINI GENERATED RESPONSE:")
        print("=" * 80)
        print(output["answer"])
        print("=" * 80)

        return output["answer"]


def main():
    """Main execution function to test user queries independently from the ingestion pipeline."""
    engine = NexaCoreRAGQueryEngine(provider="gemini")

    test_queries = [
        "What are the release trains and deployment windows for production?",
    ]

    for q in test_queries:
        engine.query(q, top_k=3)


if __name__ == "__main__":
    main()
