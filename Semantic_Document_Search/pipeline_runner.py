"""
Pipeline Ingestion & Indexing Runner for NexaCore Semantic Document Search.

Executes data processing pipeline up to vector embedding and FAISS index persistence:
Step 1: Document Loading
Step 2: Markdown Parsing
Step 3: Structure-Preserving Cleaning
Step 4: Recursive Chunking
Step 5: Vector Embedding (SentenceTransformers)
Step 6: FAISS Indexing & Disk Persistence (saves index to 'd:\\RAG\\faiss_index')
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

from document_cleaner import CleanedPage, PDFDocumentCleaner
from document_chunker import DocumentChunk, RecursiveDocumentChunker
from document_embedder import DocumentEmbedder, EmbeddedChunk
from document_loader import PDFDocumentLoader
from document_parser import PDFDocumentParser
from faiss_indexer import FAISSVectorIndex

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("PipelineRunner")


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "faiss_index"


def run_indexing_pipeline(output_dir: Optional[Union[str, Path]] = None) -> FAISSVectorIndex:
    """Execute PDF loading, parsing, cleaning, chunking, embedding, and FAISS disk saving."""
    target_dir = str(Path(output_dir if output_dir is not None else DEFAULT_OUTPUT_DIR).resolve())
    print("=" * 80)
    print(" NEXACORE SEMANTIC DOCUMENT SEARCH - DATA INGESTION & FAISS INDEXING PIPELINE")
    print("=" * 80)

    # 1. Document Loading
    logger.info("STEP 1: Starting PDF Document Loading...")
    loader = PDFDocumentLoader()
    loaded_pdfs = loader.load_all_pdfs()
    print(f"\n[Summary Step 1] Loaded {len(loaded_pdfs)} PDF files from datasource.")

    if not loaded_pdfs:
        logger.error("No PDF files were loaded. Exiting pipeline.")
        raise RuntimeError("No PDF files found.")

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

    # 4. Recursive Document Chunking
    logger.info("\nSTEP 4: Starting Recursive Document Chunking...")
    chunker = RecursiveDocumentChunker(chunk_size=800, chunk_overlap=150)
    chunks = chunker.chunk_all_pages(cleaned_pages)
    print(f"[Summary Step 4] Generated {len(chunks)} text chunks.")

    # 5. Document Embedding
    logger.info("\nSTEP 5: Generating Vector Embeddings using Sentence Transformers...")
    embedder = DocumentEmbedder()
    embedded_chunks = embedder.embed_all_chunks(chunks)
    print(f"[Summary Step 5] Embedded {len(embedded_chunks)} chunks (Vector dimension: {embedded_chunks[0].embedding.shape[0]}).")

    # 6. FAISS Vector Indexing & Disk Persistence
    logger.info("\nSTEP 6: Building FAISS Vector Index & Saving to disk...")
    vector_index = FAISSVectorIndex(dimension=embedded_chunks[0].embedding.shape[0])
    vector_index.add_embeddings(embedded_chunks)
    vector_index.save(target_dir)
    print(f"[Summary Step 6] Successfully saved {vector_index.index.ntotal} indexed vectors to '{target_dir}'.")

    # Statistics & Verification Report
    print("\n" + "=" * 80)
    print(" INGESTION & FAISS INDEXING SUMMARY REPORT")
    print("=" * 80)

    categories = {}
    total_chars_before = 0
    total_chars_after = 0

    for page in cleaned_pages:
        categories[page.category] = categories.get(page.category, 0) + 1
        total_chars_before += page.char_count_before
        total_chars_after += page.char_count_after

    chunk_sizes = [c.char_count for c in chunks]
    avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0

    print("\nDocument Page Count by Category:")
    for cat, count in categories.items():
        print(f"  - {cat:<15}: {count} pages")

    print(f"\nCharacter Statistics:")
    print(f"  - Total Raw Chars    : {total_chars_before:,}")
    print(f"  - Total Cleaned Chars: {total_chars_after:,}")

    print(f"\nChunking Statistics (Target Chunk Size: 800, Overlap: 150):")
    print(f"  - Total Chunks Generated: {len(chunks)}")
    print(f"  - Average Chunk Length  : {avg_chunk_size:.1f} characters")

    print(f"\nFAISS Index Statistics:")
    print(f"  - Output Directory   : {target_dir}")
    print(f"  - Vector Count       : {vector_index.index.ntotal}")
    print(f"  - Vector Dimensions  : {vector_index.dimension}")

    print("\n" + "=" * 80)
    print(" DOCUMENT EMBEDDING & FAISS INDEXING PIPELINE COMPLETED!")
    print("=" * 80)

    return vector_index


if __name__ == "__main__":
    run_indexing_pipeline()
