"""
Pipeline Runner for NexaCore Knowledge Base RAG (Project 2).

Orchestrates the data ingestion pipeline:
Step 1: Document Loading & Extension Filtering (.pdf, .docx, .md, .txt)
Step 2: Multi-Format Document Parsing into LlamaIndex Document objects
Step 3: Structure-Preserving Document Cleaning & Noise Reduction
"""

import logging
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from dotenv import load_dotenv

# Load environment variables from parent workspace directory
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Force UTF-8 output encoding for Windows compatibility
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        pass

# Ensure current directory and parent directory are in path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from document_loader import DocumentLoader
from document_parser import DocumentParser
from document_cleaner import DocumentCleaner
from chunking import StructureAwareChunker, SemanticChunker, HybridChunker, save_chunked_nodes
from vector_store import NexaCoreVectorStoreManager
from retriever import NexaCoreRetriever
from query_runner import NexaCoreQueryRunner
from llama_index.core import Document, VectorStoreIndex
from llama_index.core.schema import TextNode

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("PipelineRunner")


def run_ingestion_pipeline(
    datasource_dir: str = None,
    chunking_strategy: str = "structure",
    index_to_qdrant: bool = True,
    collection_name: str = "nexacore_kb",
) -> Tuple[List[TextNode], Optional[VectorStoreIndex]]:
    """Execute end-to-end LlamaIndex document loading, metadata enrichment, cleaning, chunking, and Qdrant indexing pipeline.

    Args:
        datasource_dir: Path to directory containing raw documents.
        chunking_strategy: 'structure' (StructureAwareChunker), 'hybrid', or 'semantic'.
        index_to_qdrant: Whether to embed nodes via Google GenAI and store vectors into Qdrant DB.
        collection_name: Qdrant collection name (default: 'nexacore_kb').

    Returns:
        Tuple of (List[TextNode], Optional[VectorStoreIndex])
    """
    print("=" * 80)
    print(f" NEXACORE KNOWLEDGE BASE RAG - END-TO-END INGESTION PIPELINE [{chunking_strategy.upper()}]")
    print("=" * 80)

    # Step 1: LlamaIndex SimpleDirectoryReader Document Loading
    logger.info("STEP 1: Starting Pure LlamaIndex SimpleDirectoryReader Loading...")
    loader = DocumentLoader(datasource_dir=datasource_dir)
    raw_documents = loader.load_documents()
    print(f"\n[Summary Step 1] Loaded {len(raw_documents)} raw LlamaIndex Document object(s) via SimpleDirectoryReader.")

    if not raw_documents:
        logger.error("No supported files loaded via SimpleDirectoryReader. Exiting pipeline.")
        return [], None

    # Step 2: LlamaIndex Document Metadata Enrichment
    logger.info("\nSTEP 2: Starting LlamaIndex Document Metadata Enrichment...")
    parser = DocumentParser()
    enriched_documents = parser.enrich_all_documents(raw_documents)
    print(f"[Summary Step 2] Enriched {len(enriched_documents)} LlamaIndex Document object(s) with domain metadata.")

    # Step 3: Structure-Preserving Document Cleaning
    logger.info("\nSTEP 3: Starting Structure-Preserving Cleaning & Noise Reduction...")
    cleaner = DocumentCleaner()
    cleaned_documents = cleaner.clean_all_documents(enriched_documents)
    saved_dir = cleaner.save_cleaned_documents(cleaned_documents)
    print(f"[Summary Step 3] Cleaned {len(cleaned_documents)} document records and saved files to '{saved_dir}'.")

    # Step 4: Chunking Execution & Export
    logger.info(f"\nSTEP 4: Executing {chunking_strategy.title()} Chunking...")
    if chunking_strategy.lower() == "semantic":
        chunker = SemanticChunker(breakpoint_percentile_threshold=90)
    elif chunking_strategy.lower() == "hybrid":
        chunker = HybridChunker(breakpoint_percentile_threshold=90)
    else:
        chunker = StructureAwareChunker(max_chunk_size=512, chunk_overlap=50)

    nodes = chunker.parse_all_documents(cleaned_documents)
    saved_chunks_dir = save_chunked_nodes(nodes)
    print(f"[Summary Step 4] Generated {len(nodes)} {chunking_strategy} LlamaIndex Node(s) across {len(cleaned_documents)} documents and saved to '{saved_chunks_dir}'.")

    # Step 5: Google GenAI Embeddings & Qdrant Vector Indexing
    vector_index = None
    if index_to_qdrant:
        logger.info(f"\nSTEP 5: Starting Google GenAI Embedding & Qdrant Vector DB Indexing...")
        vdb_manager = NexaCoreVectorStoreManager(collection_name=collection_name)
        vector_index = vdb_manager.index_nodes(nodes)
        print(f"[Summary Step 5] Successfully indexed {len(nodes)} vector embeddings into Qdrant collection '{collection_name}'!")
    else:
        logger.info("\nSTEP 5: Qdrant Indexing skipped as requested.")

    # Generate Summary Report
    print("\n" + "=" * 80)
    print(" INGESTION, METADATA & CHUNKING SUMMARY REPORT")
    print("=" * 80)

    departments = {}
    doc_types = {}
    file_types = {}
    sections_count = 0

    for node in nodes:
        dept = node.metadata.get("department", "unknown")
        dtype = node.metadata.get("document_type", "unknown")
        ftype = node.metadata.get("file_type", "unknown")
        departments[dept] = departments.get(dept, 0) + 1
        doc_types[dtype] = doc_types.get(dtype, 0) + 1
        file_types[ftype] = file_types.get(ftype, 0) + 1
        if node.metadata.get("section"):
            sections_count += 1

    print("\n1. Structured Chunks (Nodes) by Department:")
    for dept, count in departments.items():
        print(f"   - {dept:<15}: {count} node(s)")

    print("\n2. Structured Chunks (Nodes) by Document Type:")
    for dtype, count in doc_types.items():
        print(f"   - {dtype:<20}: {count} node(s)")

    print("\n3. Structured Chunks (Nodes) by Source Extension:")
    for ftype, count in file_types.items():
        print(f"   - {ftype.upper():<15}: {count} node(s)")

    print("\n4. Structure Metadata Stats:")
    print(f"   - Total Documents Processed: {len(cleaned_documents)}")
    print(f"   - Total LlamaIndex Nodes   : {len(nodes)}")
    print(f"   - Nodes with Section Tag   : {sections_count} ({sections_count / len(nodes) * 100:.1f}%)")

    print("\n5. Sample LlamaIndex Structured Node Schema:")
    if nodes:
        sample_node = nodes[0]
        print(f"   - Node ID    : {sample_node.node_id}")
        print(f"   - Text Length: {len(sample_node.text)} chars")
        print("   - Metadata Dictionary:")
        for key, val in sample_node.metadata.items():
            print(f"     * {key:<22}: {val}")

        print("\n6. Sample Citation Preview:")
        try:
            from metadata import format_citation_label
            print(f"   - Citation Label: {format_citation_label(sample_node.metadata)}")
        except ImportError:
            pass

    print("\n" + "=" * 80)
    print(" END-TO-END RAG INGESTION & VECTOR INDEXING PIPELINE COMPLETED!")
    print("=" * 80)

    return nodes, vector_index


if __name__ == "__main__":
    run_ingestion_pipeline(chunking_strategy="structure", index_to_qdrant=True)
