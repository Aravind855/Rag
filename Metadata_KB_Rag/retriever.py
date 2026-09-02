"""
Metadata-Aware Retriever Module for NexaCore Knowledge Base RAG (Project 2).

Provides NexaCoreRetriever for executing vector similarity searches in Qdrant with:
1. Multi-field Metadata Filtering (department, document_type, file_type, category)
2. Score thresholding and top-k filtering
3. Structured context formatting with citation labels for LLM grounding
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from dotenv import load_dotenv
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.vector_stores.types import (
    ExactMatchFilter,
    MetadataFilter,
    MetadataFilters,
)

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Add current module directory to path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from metadata import format_citation_label
from vector_store import DEFAULT_COLLECTION_NAME, NexaCoreVectorStoreManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("NexaCoreRetriever")


class NexaCoreRetriever:
    """Metadata-Aware Vector Retriever targeting Qdrant DB."""

    def __init__(
        self,
        vector_store_manager: Optional[NexaCoreVectorStoreManager] = None,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        default_top_k: int = 5,
    ):
        """Initialize retriever with an active NexaCoreVectorStoreManager.

        Args:
            vector_store_manager: Optional pre-configured manager instance.
            collection_name: Name of target Qdrant collection.
            default_top_k: Default number of top results to retrieve.
        """
        if vector_store_manager is None:
            self.vdb_manager = NexaCoreVectorStoreManager(collection_name=collection_name)
        else:
            self.vdb_manager = vector_store_manager

        self.default_top_k = default_top_k
        logger.info(
            f"Initialized NexaCoreRetriever [Collection='{self.vdb_manager.collection_name}', "
            f"default_top_k={default_top_k}]"
        )

    def retrieve(
        self,
        query: str,
        department: Optional[str] = None,
        document_type: Optional[str] = None,
        file_type: Optional[str] = None,
        category: Optional[str] = None,
        top_k: Optional[int] = None,
        min_score: Optional[float] = None,
    ) -> List[NodeWithScore]:
        """Perform metadata-filtered vector search in Qdrant.

        Args:
            query: User search query string.
            department: Filter by department (e.g., 'hr', 'engineering', 'finance').
            document_type: Filter by document classification (e.g., 'policy_document', 'technical_standard').
            file_type: Filter by file extension (e.g., 'pdf', 'docx', 'md').
            category: Filter by high-level category/department.
            top_k: Max number of results to return (defaults to self.default_top_k).
            min_score: Optional minimum similarity score threshold.

        Returns:
            List of LlamaIndex NodeWithScore results.
        """
        limit = top_k if top_k is not None else self.default_top_k
        clean_query = query.strip()

        if not clean_query:
            logger.warning("Empty query string passed to retriever. Returning empty list.")
            return []

        # Build MetadataFilter payload conditions
        filters_list: List[MetadataFilter] = []
        if department:
            filters_list.append(ExactMatchFilter(key="department", value=department.strip().lower()))
        if document_type:
            filters_list.append(ExactMatchFilter(key="document_type", value=document_type.strip().lower()))
        if file_type:
            clean_ft = file_type.strip().lstrip(".").lower()
            filters_list.append(ExactMatchFilter(key="file_type", value=clean_ft))
        if category:
            filters_list.append(ExactMatchFilter(key="category", value=category.strip().lower()))

        metadata_filters = MetadataFilters(filters=filters_list) if filters_list else None

        logger.info(
            f"Executing Retrieval: query='{clean_query}' | filters=[dept={department}, "
            f"doc_type={document_type}, file_type={file_type}] | top_k={limit}"
        )

        try:
            index = self.vdb_manager.load_existing_index()
            retriever = index.as_retriever(
                similarity_top_k=limit,
                filters=metadata_filters,
            )
            raw_results = retriever.retrieve(clean_query)

            # Apply score thresholding if specified
            if min_score is not None:
                filtered_results = [res for res in raw_results if res.score is not None and res.score >= min_score]
            else:
                filtered_results = raw_results

            logger.info(f"Retrieved {len(filtered_results)} matching node(s) after metadata filtering & score pruning.")
            return filtered_results

        except Exception as err:
            logger.error(f"Error executing vector retrieval: {err}", exc_info=True)
            return []

    def format_retrieved_context(self, nodes_with_scores: List[NodeWithScore]) -> str:
        """Format retrieved nodes into a structured, grounded context block for LLM prompting.

        Args:
            nodes_with_scores: List of retrieved NodeWithScore objects.

        Returns:
            Formatted string containing citation headers and text content.
        """
        if not nodes_with_scores:
            return "NO RELEVANT CONTEXT FOUND IN KNOWLEDGE BASE."

        formatted_blocks = []
        for idx, res in enumerate(nodes_with_scores, 1):
            node = res.node
            meta = node.metadata or {}
            citation = format_citation_label(meta)
            score_str = f"{res.score:.4f}" if res.score is not None else "N/A"

            block = (
                f"--- CONTEXT BLOCK [{idx}] (Similarity Score: {score_str}) ---\n"
                f"Citation Header : {citation}\n"
                f"Source File     : {meta.get('source', 'Unknown')}\n"
                f"Department      : {meta.get('department', 'General').upper()}\n"
                f"Document Type   : {meta.get('document_type', 'General')}\n"
                f"Section/Header  : {meta.get('section') or meta.get('header_path') or 'N/A'}\n"
                f"Text Content    :\n{node.text.strip()}\n"
            )
            formatted_blocks.append(block)

        return "\n".join(formatted_blocks)


if __name__ == "__main__":
    print("=" * 80)
    print(" NEXACORE KB RAG - METADATA-AWARE RETRIEVER TEST")
    print("=" * 80)

    try:
        retriever = NexaCoreRetriever(collection_name="nexacore_kb")

        test_query = "What is the policy for leave and work from home?"
        print(f"\n1. Unfiltered Query Test: '{test_query}'")
        unfiltered_nodes = retriever.retrieve(query=test_query, top_k=3)
        print(retriever.format_retrieved_context(unfiltered_nodes[:2]))

        print(f"\n2. Department-Filtered Query Test (dept='hr'):")
        hr_nodes = retriever.retrieve(query=test_query, department="hr", top_k=3)
        for idx, n in enumerate(hr_nodes, 1):
            print(f"   [{idx}] Score: {n.score:.4f} | Dept: {n.node.metadata.get('department')} | Source: {n.node.metadata.get('source')}")

        print("\n" + "=" * 80)
        print(" RETRIEVER TEST COMPLETED SUCCESSFULLY!")
        print("=" * 80)

    except Exception as ex:
        logger.error(f"Retriever Test Failed: {ex}", exc_info=True)
        sys.exit(1)
