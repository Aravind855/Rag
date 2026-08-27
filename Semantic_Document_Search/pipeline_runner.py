"""
Pipeline Runner for NexaCore Semantic Document Search (Project 1 - Steps 1-3).

Demonstrates and validates end-to-end PDF Document Loading, Parsing,
and Structure-Preserving Cleaning.
"""

import logging
import sys
from typing import List

# Force UTF-8 encoding on standard output for Windows console compatibility
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        pass

from document_cleaner import CleanedPage, PDFDocumentCleaner
from document_loader import PDFDocumentLoader
from document_parser import PDFDocumentParser

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("PipelineRunner")


def run_pipeline() -> List[CleanedPage]:
    """Execute the Document Loading, Parsing, and Cleaning pipeline."""
    print("=" * 80)
    print(" NEXACORE SEMANTIC DOCUMENT SEARCH - DATA PIPELINE (STEPS 1-3)")
    print("=" * 80)

    # 1. Document Loading
    logger.info("STEP 1: Starting PDF Document Loading...")
    loader = PDFDocumentLoader()
    loaded_pdfs = loader.load_all_pdfs()
    print(f"\n[Summary Step 1] Loaded {len(loaded_pdfs)} PDF files from datasource.")

    if not loaded_pdfs:
        logger.error("No PDF files were loaded. Exiting pipeline.")
        return []

    # 2. Document Parsing
    logger.info("\nSTEP 2: Starting Page-by-Page Document Parsing...")
    parser = PDFDocumentParser()
    parsed_pages = parser.parse_all_documents(loaded_pdfs)
    print(f"[Summary Step 2] Extracted {len(parsed_pages)} total page records.")

    # 3. Document Cleaning
    logger.info("\nSTEP 3: Starting Structure-Preserving Document Cleaning...")
    cleaner = PDFDocumentCleaner()
    cleaned_pages = cleaner.clean_all_pages(parsed_pages)
    print(f"[Summary Step 3] Successfully cleaned {len(cleaned_pages)} pages.")

    # Clean up PDF handles
    for pdf in loaded_pdfs:
        pdf.close()


    # Statistics & Verification Report
    print("\n" + "=" * 80)
    print(" DATA PROCESSING SUMMARY & VERIFICATION REPORT")
    print("=" * 80)
    
    categories = {}
    total_chars_before = 0
    total_chars_after = 0

    for page in cleaned_pages:
        categories[page.category] = categories.get(page.category, 0) + 1
        total_chars_before += page.char_count_before
        total_chars_after += page.char_count_after

    print("\nPage Count by Category:")
    for cat, count in categories.items():
        print(f"  - {cat:<15}: {count} pages")

    print(f"\nCharacter Statistics:")
    print(f"  - Total Characters (Raw)    : {total_chars_before:,}")
    print(f"  - Total Characters (Cleaned): {total_chars_after:,}")
    print(f"  - Normalization Difference  : {total_chars_before - total_chars_after:,} chars removed/normalized")

    print("\n" + "-" * 80)
    print(" SAMPLE OUTPUT INSPECTION (PRESERVING DOCUMENT STRUCTURE)")
    print("-" * 80)

    # Print a sample page preview from HR and Engineering
    samples_to_show = ["hr", "engineering"]
    shown = set()
    for page in cleaned_pages:
        if page.category in samples_to_show and page.category not in shown:
            shown.add(page.category)
            print(f"\n[Category: {page.category.upper()} | Source: {page.source_file} | Page {page.page_number}/{page.total_pages}]")
            print("Preview (First 350 chars):\n")
            print(page.text[:350])
            print("...")

    print("\n" + "=" * 80)
    print(" STEPS 1-3 COMPLETED SUCCESSFULLY!")
    print("=" * 80)

    return cleaned_pages


if __name__ == "__main__":
    run_pipeline()
