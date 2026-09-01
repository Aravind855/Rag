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
from typing import List

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
from llama_index.core import Document

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("PipelineRunner")


def run_ingestion_pipeline(datasource_dir: str = None) -> List[Document]:
    """Execute pure LlamaIndex document loading, metadata enrichment, and cleaning pipeline."""
    print("=" * 80)
    print(" NEXACORE KNOWLEDGE BASE RAG - PURE LLAMAINDEX INGESTION PIPELINE")
    print("=" * 80)

    # Step 1: LlamaIndex SimpleDirectoryReader Document Loading
    logger.info("STEP 1: Starting Pure LlamaIndex SimpleDirectoryReader Loading...")
    loader = DocumentLoader(datasource_dir=datasource_dir)
    raw_documents = loader.load_documents()
    print(f"\n[Summary Step 1] Loaded {len(raw_documents)} raw LlamaIndex Document object(s) via SimpleDirectoryReader.")

    if not raw_documents:
        logger.error("No supported files loaded via SimpleDirectoryReader. Exiting pipeline.")
        return []

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

    # Generate Summary Report
    print("\n" + "=" * 80)
    print(" INGESTION & CLEANING SUMMARY REPORT (PHASE 1)")
    print("=" * 80)

    departments = {}
    doc_types = {}
    file_types = {}
    total_raw_chars = 0
    total_cleaned_chars = 0

    for doc in cleaned_documents:
        dept = doc.metadata.get("department", doc.metadata.get("category", "unknown"))
        dtype = doc.metadata.get("document_type", "unknown")
        ftype = doc.metadata.get("file_type", "unknown")
        departments[dept] = departments.get(dept, 0) + 1
        doc_types[dtype] = doc_types.get(dtype, 0) + 1
        file_types[ftype] = file_types.get(ftype, 0) + 1
        total_raw_chars += doc.metadata.get("char_count_before", 0)
        total_cleaned_chars += doc.metadata.get("char_count_after", 0)

    print("\n1. Document Records by Department:")
    for dept, count in departments.items():
        print(f"   - {dept:<15}: {count} document(s)")

    print("\n2. Document Records by Inferred Document Type:")
    for dtype, count in doc_types.items():
        print(f"   - {dtype:<20}: {count} document(s)")

    print("\n3. Document Records by File Extension:")
    for ftype, count in file_types.items():
        print(f"   - {ftype.upper():<15}: {count} document(s)")

    print("\n4. Character Statistics:")
    print(f"   - Total Raw Chars    : {total_raw_chars:,}")
    print(f"   - Total Cleaned Chars: {total_cleaned_chars:,}")

    reduction = total_raw_chars - total_cleaned_chars
    reduction_pct = (reduction / total_raw_chars * 100.0) if total_raw_chars > 0 else 0.0
    print(f"   - Boilerplate Removed: {reduction:,} chars ({reduction_pct:.2f}%)")

    print("\n5. Sample LlamaIndex Document Metadata Schema:")
    if cleaned_documents:
        sample_doc = cleaned_documents[0]
        print(f"   - Document ID: {sample_doc.doc_id}")
        for key, val in sample_doc.metadata.items():
            print(f"     * {key:<22}: {val}")

    print("\n" + "=" * 80)
    print(" PHASE 1: INGESTION PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 80)

    return cleaned_documents


if __name__ == "__main__":
    run_ingestion_pipeline()
