"""
Qdrant Vector Database Integration for NexaCore Knowledge Base RAG (Project 2).

Manages vector embedding storage, payload metadata indexing, and metadata-aware retrieval.
Supports:
1. Qdrant Cloud (via QDRANT_URL and QDRANT_API_KEY environment variables)
2. Local Persistent Qdrant (path='./qdrant_data') fallback
3. In-Memory Qdrant (location=':memory:') fallback
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import qdrant_client
from dotenv import load_dotenv
from llama_index.core import Settings, StorageContext, VectorStoreIndex
from llama_index.core.vector_stores.types import (
    ExactMatchFilter,
    MetadataFilter,
    MetadataFilters,
)
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.vector_stores.qdrant import QdrantVectorStore

from embeddings import configure_global_llamaindex_embeddings, get_embedding_model

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("QdrantVectorStoreManager")

DEFAULT_COLLECTION_NAME = "nexacore_kb"


class NexaCoreVectorStoreManager:
    """Manager for Qdrant Vector Store connection, indexing, and metadata-filtered retrieval."""

    def __init__(
        self,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        qdrant_url: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
        prefer_grpc: bool = False,
    ):
        self.collection_name = collection_name
        self.qdrant_url = qdrant_url or os.getenv("QDRANT_URL")
        self.qdrant_api_key = qdrant_api_key or os.getenv("QDRANT_API_KEY")
        self.prefer_grpc = prefer_grpc

        # Initialize Qdrant Client (Cloud vs Local Fallback)
        self.client = self._connect_qdrant_client()

        # Configure Global LlamaIndex Embedding Model (Google GenAI)
        self.embed_model = configure_global_llamaindex_embeddings()

        # Initialize LlamaIndex QdrantVectorStore with smaller batch size
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            batch_size=32,
        )

        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        self.ensure_payload_indexes()
        logger.info(f"Initialized NexaCoreVectorStoreManager targeting collection '{self.collection_name}'.")

    def ensure_payload_indexes(self) -> None:
        """Ensure Qdrant payload keyword indexes exist for filtered metadata fields."""
        from qdrant_client.http import models as qmodels
        fields = ["department", "document_type", "file_type", "category"]
        for field in fields:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field,
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                )
                logger.info(f"Ensured Qdrant payload index for field '{field}' in collection '{self.collection_name}'.")
            except Exception:
                pass

    def _connect_qdrant_client(self) -> qdrant_client.QdrantClient:
        """Connect to Qdrant Cloud if credentials exist, otherwise fall back to local disk/memory."""
        if self.qdrant_url and self.qdrant_url.strip():
            url = self.qdrant_url.strip()
            logger.info(f"Connecting to Qdrant Cloud cluster at: '{url}'")
            try:
                client = qdrant_client.QdrantClient(
                    url=url,
                    api_key=self.qdrant_api_key,
                    prefer_grpc=self.prefer_grpc,
                    timeout=180.0,
                )
                # Quick health check
                client.get_collections()
                logger.info("Successfully connected to Qdrant Cloud Cluster!")
                return client
            except Exception as err:
                logger.warning(
                    f"Could not connect to Qdrant Cloud ({err}). "
                    "Falling back to local disk storage."
                )

        # Fallback 1: Local Disk Storage
        local_db_path = Path(__file__).resolve().parent / "qdrant_data"
        local_db_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using local Qdrant persistent storage at: '{local_db_path}'")
        return qdrant_client.QdrantClient(path=str(local_db_path))

    def index_nodes(
        self,
        nodes: List[TextNode],
        show_progress: bool = True,
        ) -> VectorStoreIndex:
        """Embed nodes and index vector embeddings + metadata payloads into Qdrant.

        Args:
            nodes: List of LlamaIndex TextNode objects.
            show_progress: Display progress bar during embedding generation.

        Returns:
            Built LlamaIndex VectorStoreIndex.
        """
        if not nodes:
            logger.warning("No nodes provided for indexing.")
            return VectorStoreIndex([], storage_context=self.storage_context)

        logger.info(f"Starting Qdrant indexing for {len(nodes)} node(s)...")

        # Build VectorStoreIndex (LlamaIndex automatically embeds nodes and pushes to Qdrant payload)
        index = VectorStoreIndex(
            nodes=nodes,
            storage_context=self.storage_context,
            show_progress=show_progress,
        )

        logger.info(
            f"Successfully indexed {len(nodes)} vector embeddings into Qdrant collection '{self.collection_name}'!"
        )
        return index

    def load_existing_index(self) -> VectorStoreIndex:
        """Load an existing Qdrant collection as a VectorStoreIndex."""
        index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            storage_context=self.storage_context,
        )
        logger.info(f"Loaded existing index from Qdrant collection '{self.collection_name}'.")
        return index

    def search_with_filters(
        self,
        query_text: str,
        department: Optional[str] = None,
        document_type: Optional[str] = None,
        file_type: Optional[str] = None,
        top_k: int = 5,
    ) -> List[NodeWithScore]:
        """Perform vector similarity search in Qdrant with optional metadata payload filters.

        Args:
            query_text: User search query string.
            department: Optional department metadata filter (e.g., 'hr', 'engineering').
            document_type: Optional document type filter (e.g., 'company_policy').
            file_type: Optional file extension filter (e.g., '.pdf', '.docx').
            top_k: Number of top scoring matches to return.

        Returns:
            List of LlamaIndex NodeWithScore results.
        """
        # Construct MetadataFilters array
        filter_list = []
        if department:
            filter_list.append(ExactMatchFilter(key="department", value=department.lower()))
        if document_type:
            filter_list.append(ExactMatchFilter(key="document_type", value=document_type.lower()))
        if file_type:
            filter_list.append(ExactMatchFilter(key="file_type", value=file_type.lower()))

        metadata_filters = MetadataFilters(filters=filter_list) if filter_list else None

        index = self.load_existing_index()
        retriever = index.as_retriever(
            similarity_top_k=top_k,
            filters=metadata_filters,
        )

        results = retriever.retrieve(query_text)
        logger.info(
            f"Retrieved {len(results)} matching node(s) for query: '{query_text}' "
            f"[Filters: dept={department}, doc_type={document_type}]"
        )
        return results


if __name__ == "__main__":
    print("=" * 80)
    print(" NEXACORE KB RAG - QDRANT VECTOR STORE & FILTERED RETRIEVAL TEST")
    print("=" * 80)

    try:
        from document_cleaner import DocumentCleaner
        from document_loader import DocumentLoader
        from document_parser import DocumentParser
        from chunking import StructureAwareChunker

        # 1. Load & Process Sample Documents
        loader = DocumentLoader()
        parser = DocumentParser()
        cleaner = DocumentCleaner()
        chunker = StructureAwareChunker()

        raw_docs = loader.load_documents()
        enriched_docs = parser.enrich_all_documents(raw_docs)
        cleaned_docs = cleaner.clean_all_documents(enriched_docs)
        nodes = chunker.parse_all_documents(cleaned_docs)

        # Take top 10 sample nodes for rapid indexing verification
        sample_nodes = nodes[:10]

        # 2. Initialize Qdrant Manager & Index Sample Nodes
        vdb_manager = NexaCoreVectorStoreManager(collection_name="test_nexacore_kb")
        index = vdb_manager.index_nodes(sample_nodes, show_progress=False)

        # 3. Test Vector Search WITHOUT Filters
        test_query = "What are the API design guidelines?"
        print(f"\n1. Vector Similarity Search (Unfiltered): Query = '{test_query}'")
        unfiltered_results = vdb_manager.search_with_filters(query_text=test_query, top_k=3)
        for idx, res in enumerate(unfiltered_results, 1):
            print(f"   [{idx}] Score: {res.score:.4f} | Dept: {res.node.metadata.get('department')} | Source: {res.node.metadata.get('source')}")

        # 4. Test Vector Search WITH Metadata Filter (department='engineering')
        print(f"\n2. Vector Similarity Search WITH Metadata Filter (department='engineering'):")
        filtered_results = vdb_manager.search_with_filters(
            query_text=test_query,
            department="engineering",
            top_k=3,
        )
        for idx, res in enumerate(filtered_results, 1):
            print(f"   [{idx}] Score: {res.score:.4f} | Dept: {res.node.metadata.get('department')} | Source: {res.node.metadata.get('source')}")

        print("\n" + "=" * 80)
        print(" QDRANT VECTOR STORE TEST COMPLETED SUCCESSFULLY!")
        print("=" * 80)

    except Exception as ex:
        logger.error(f"Qdrant Vector Store Test Failed: {ex}", exc_info=True)
        sys.exit(1)
