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
    """Execute document discovery, multi-format parsing, and structure-preserving cleaning."""
    print("=" * 80)
    print(" NEXACORE KNOWLEDGE BASE RAG - DATA INGESTION & CLEANING PIPELINE")
    print("=" * 80)

    # Step 1: Document Discovery & Filtering
    logger.info("STEP 1: Starting Document Discovery & Extension Filtering...")
    loader = DocumentLoader(datasource_dir=datasource_dir)
    discovered_files = loader.discover_files()
    print(f"\n[Summary Step 1] Discovered {len(discovered_files)} supported files (.pdf, .docx, .md, .txt).")

    if not discovered_files:
        logger.error("No supported files discovered. Exiting ingestion pipeline.")
        return []

    # Step 2: Multi-Format Document Parsing
    logger.info("\nSTEP 2: Starting Multi-Format Document Parsing...")
    parser = DocumentParser()
    parsed_documents = parser.parse_all_files(discovered_files)
    print(f"[Summary Step 2] Generated {len(parsed_documents)} LlamaIndex Document objects.")

    # Step 3: Structure-Preserving Document Cleaning
    logger.info("\nSTEP 3: Starting Structure-Preserving Cleaning & Noise Reduction...")
    cleaner = DocumentCleaner()
    cleaned_documents = cleaner.clean_all_documents(parsed_documents)
    saved_dir = cleaner.save_cleaned_documents(cleaned_documents)
    print(f"[Summary Step 3] Cleaned {len(cleaned_documents)} document records and saved files to '{saved_dir}'.")

    # Generate Summary Report
    print("\n" + "=" * 80)
    print(" INGESTION & CLEANING SUMMARY REPORT")
    print("=" * 80)

    categories = {}
    file_types = {}
    total_raw_chars = 0
    total_cleaned_chars = 0

    for doc in cleaned_documents:
        cat = doc.metadata.get("category", "unknown")
        ftype = doc.metadata.get("file_type", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
        file_types[ftype] = file_types.get(ftype, 0) + 1
        total_raw_chars += doc.metadata.get("char_count_before", 0)
        total_cleaned_chars += doc.metadata.get("char_count_after", 0)

    print("\n1. Document Records by Category:")
    for cat, count in categories.items():
        print(f"   - {cat:<15}: {count} document pages/sections")

    print("\n2. Document Records by File Extension:")
    for ftype, count in file_types.items():
        print(f"   - {ftype.upper():<15}: {count} documents")

    print("\n3. Character Statistics:")
    print(f"   - Total Raw Chars    : {total_raw_chars:,}")
    print(f"   - Total Cleaned Chars: {total_cleaned_chars:,}")

    reduction = total_raw_chars - total_cleaned_chars
    reduction_pct = (reduction / total_raw_chars * 100.0) if total_raw_chars > 0 else 0.0
    print(f"   - Boilerplate Removed: {reduction:,} chars ({reduction_pct:.2f}%)")

    print("\n" + "=" * 80)
    print(" INGESTION PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 80)

    return cleaned_documents


if __name__ == "__main__":
    run_ingestion_pipeline()
