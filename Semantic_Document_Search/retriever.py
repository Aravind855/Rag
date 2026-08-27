"""
Retriever Module for NexaCore Semantic Document Search.

Combines DocumentEmbedder and FAISSVectorIndex to perform semantic retrieval
and format retrieved context blocks for RAG generation.
"""

import logging
import sys
from pathlib import Path
from typing import List, Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))
from document_embedder import DocumentEmbedder
from faiss_indexer import FAISSVectorIndex, SearchResult

logger = logging.getLogger(__name__)


class DocumentRetriever:
    """Handles semantic retrieval over indexed FAISS vector database."""

    def __init__(self, vector_index: FAISSVectorIndex, embedder: DocumentEmbedder):
        self.vector_index = vector_index
        self.embedder = embedder

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        category_filter: Optional[str] = None,
    ) -> List[SearchResult]:
        """Retrieve top-k search results matching the query."""
        logger.info(f"Retrieving top {top_k} results for query: '{query}'...")
        results = self.vector_index.search_query(
            query_text=query,
            embedder=self.embedder,
            top_k=top_k,
            category_filter=category_filter,
        )
        logger.info(f"Retrieved {len(results)} relevant chunk(s).")
        return results

    def format_retrieved_context(self, results: List[SearchResult]) -> str:
        """Format retrieved SearchResult items into a clear text context block for LLM prompt."""
        if not results:
            return "No relevant context found in documents."

        formatted_blocks = []
        for idx, res in enumerate(results, 1):
            block = (
                f"[Doc {idx} | File: {res.source_file} | Page: {res.page_number} | "
                f"Category: {res.category} | Score: {res.score:.4f}]\n"
                f"{res.text.strip()}"
            )
            formatted_blocks.append(block)

        return "\n\n" + ("=" * 40) + "\n\n".join(formatted_blocks) + "\n" + ("=" * 40)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("DocumentRetriever module ready.")
