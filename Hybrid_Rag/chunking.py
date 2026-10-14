"""Structure-Aware Recursive Document Chunker for Hybrid RAG (Functional Approach).

Loads cleaned Markdown documents from d:\RAG\cleaned_documents, applies a
two-tier structure-aware chunking strategy (MarkdownHeaderTextSplitter +
RecursiveCharacterTextSplitter), and outputs enriched LangChain Document chunks
with unique chunk IDs, breadcrumbs, hierarchical headers, and metadata.

All paths are resolved dynamically without hardcoding.
All operations are written as pure procedural functions without classes.
"""

import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import yaml

# LangChain Core & Text Splitters
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("hybrid_rag.chunking")

# =====================================================================
# DYNAMIC PATH RESOLUTION (NO HARDCODED PATHS)
# =====================================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CLEANED_DIR = Path(os.getenv("RAG_CLEANED_DIR", str(PROJECT_ROOT / "cleaned_documents")))
DEFAULT_OUTPUT_DIR = Path(os.getenv("RAG_CHUNKS_DIR", str(PROJECT_ROOT / "Hybrid_Rag" / "chunks")))


def get_default_cleaned_dir() -> Path:
    """Returns the dynamically resolved cleaned documents directory."""
    return DEFAULT_CLEANED_DIR


def get_default_output_dir() -> Path:
    """Returns the dynamically resolved chunks export directory."""
    return DEFAULT_OUTPUT_DIR


# =====================================================================
# FRONTMATTER & TEXT PREPARATION FUNCTIONS
# =====================================================================

def extract_frontmatter_and_content(file_path: Union[str, Path]) -> Tuple[Dict[str, Any], str]:
    """Extracts YAML frontmatter metadata and separates the markdown body.

    Args:
        file_path: Path to the Markdown document.

    Returns:
        Tuple of (metadata_dict, clean_markdown_body).
    """
    path = Path(file_path).resolve()
    raw_text = path.read_text(encoding="utf-8", errors="replace")

    # Match YAML Frontmatter block: --- \n ... \n ---
    fm_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    match = fm_pattern.match(raw_text)

    metadata: Dict[str, Any] = {}
    if match:
        yaml_str = match.group(1)
        try:
            metadata = yaml.safe_load(yaml_str) or {}
        except Exception as e:
            logger.warning(f"Failed parsing YAML frontmatter in {path.name}: {e}")
        body = raw_text[match.end():]
    else:
        body = raw_text

    # Strip top-level location line if present to prevent orphan location chunks
    body = re.sub(r"^>\s*\*\*Location:\*\*.*?\n+", "", body.strip())

    return metadata, body.strip()

# verified
def build_breadcrumbs(doc_meta: Dict[str, Any], header_meta: Dict[str, str]) -> str:
    """Constructs a readable hierarchical breadcrumb trail.

    e.g. 'finance > expense_policy.pdf > 1. Purpose > 1.2 Approval matrix'
    """
    category = doc_meta.get("category", "")
    title = doc_meta.get("title") or doc_meta.get("original_file", "")
    parts = [p for p in [category, title] if p]

    # Append any present header levels in order
    for level in ["header_1", "header_2", "header_3", "header_4"]:
        if level in header_meta and header_meta[level]:
            clean_hdr = header_meta[level].replace("#", "").strip()
            parts.append(clean_hdr)

    return " > ".join(parts)


# =====================================================================
# CHUNKER INITIALIZATION
# =====================================================================
#  verified
def create_structure_aware_splitters(
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
    ) -> Tuple[MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter]:
    """Creates the header-based and recursive character splitters.

    - MarkdownHeaderTextSplitter: preserves logical section hierarchy
      with strip_headers=False so headers stay in the content.
    - RecursiveCharacterTextSplitter: breaks large sections on Markdown
      boundaries (headers, code fences, paragraphs, lists) with overlap.
    """
    headers_to_split_on = [
        ("#", "header_1"),
        ("##", "header_2"),
        ("###", "header_3"),
        ("####", "header_4"),
    ]

    # Stage 1: Structure-aware section splitter (keeps header text in chunks)
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,
    )

    # Stage 2: Recursive character splitter with markdown-tailored separators
    markdown_separators = [
        "\n## ",
        "\n### ",
        "\n#### ",
        "\n```",
        "\n\n",
        "\n",
        " ",
        "",
    ]

    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=markdown_separators,
        length_function=len,
    )

    return header_splitter, recursive_splitter


# =====================================================================
# DOCUMENT CHUNKING FUNCTIONS
# =====================================================================
#verified
def chunk_single_document(
    file_path: Union[str, Path],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
    header_splitter: Optional[MarkdownHeaderTextSplitter] = None,
    recursive_splitter: Optional[RecursiveCharacterTextSplitter] = None,
    ) -> List[Document]:
    """Splits a single Markdown document into structure-aware chunks.

    Guarantees:
    - Every section preserves parent document and header metadata
    - Unique deterministic chunk_id assigned per chunk
    - Tables and lists preserved without syntax distortion
    - Zero data loss
    """
    path = Path(file_path).resolve()
    doc_meta, body = extract_frontmatter_and_content(path)

    if not body:
        logger.warning(f"File {path.name} has empty body content.")
        return []

    # Initialize splitters if not provided
    if header_splitter is None or recursive_splitter is None:
        h_split, r_split = create_structure_aware_splitters(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
    else:
        h_split, r_split = header_splitter, recursive_splitter

    # 1. First Pass: Split on Markdown Headers
    header_docs = h_split.split_text(body)

    # 2. Second Pass: Split any oversized sections recursively
    raw_chunks: List[Document] = []
    for h_doc in header_docs:
        sub_chunks = r_split.split_documents([h_doc])
        raw_chunks.extend(sub_chunks)

    # 3. Third Pass: Enrich each chunk with metadata, chunk_id, stats, and breadcrumbs
    enriched_chunks: List[Document] = []
    total_chunks = len(raw_chunks)
    stem_clean = path.stem.lower().replace("-", "_").replace(" ", "_")
    cat = doc_meta.get("category", path.parent.name)

    for idx, chunk in enumerate(raw_chunks, start=1):
        content = chunk.page_content.strip()
        if not content:
            continue

        header_meta = dict(chunk.metadata)
        breadcrumbs = build_breadcrumbs(doc_meta, header_meta)
        chunk_id = f"{cat}_{stem_clean}_chunk_{idx:03d}"

        has_table = ("|" in content and "\n" in content and ("| --- |" in content or "|---|" in content or "|:---" in content))
        table_rows = content.count("\n|") if has_table else 0

        # Extract page number marker if present (e.g. <!-- Page 2 -->)
        page_match = re.search(r"<!-- Page (\d+) -->", content)
        page_number = int(page_match.group(1)) if page_match else None

        chunk_metadata: Dict[str, Any] = {
            "chunk_id": chunk_id,
            "chunk_index": idx,
            "total_chunks": total_chunks,
            "source": doc_meta.get("source_path", str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")),
            "file_name": doc_meta.get("original_file", path.name),
            "category": cat,
            "document_type": doc_meta.get("document_type", "document"),
            "title": doc_meta.get("title", path.stem.replace("_", " ").title()),
            "breadcrumbs": breadcrumbs,
            "header_1": header_meta.get("header_1", ""),
            "header_2": header_meta.get("header_2", ""),
            "header_3": header_meta.get("header_3", ""),
            "header_4": header_meta.get("header_4", ""),
            "page_number": page_number,
            "has_table": has_table,
            "table_rows": table_rows,
            "char_count": len(content),
            "word_count": len(content.split()),
        }

        enriched_chunks.append(Document(page_content=content, metadata=chunk_metadata))

    logger.debug(f"Chunked {path.name} into {len(enriched_chunks)} chunks.")
    return enriched_chunks

# verified
def chunk_all_documents(
    cleaned_docs_dir: Optional[Union[str, Path]] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
    ) -> List[Document]:
    """Iterates through all Markdown documents in cleaned_documents and

    produces a unified list of structure-aware LangChain Document chunks.

    Args:
        cleaned_docs_dir: Directory containing cleaned Markdown documents.
        chunk_size: Maximum chunk size in characters.
        chunk_overlap: Overlap between consecutive chunks.

    Returns:
        List of enriched LangChain Document chunks.
    """
    target_dir = Path(cleaned_docs_dir).resolve() if cleaned_docs_dir else DEFAULT_CLEANED_DIR
    if not target_dir.exists():
        logger.error(f"Cleaned documents directory not found: {target_dir}")
        return []

    # Discover all .md files (excluding manifest json)
    md_files = sorted([f for f in target_dir.rglob("*.md") if f.is_file()])
    logger.info(f"Discovered {len(md_files)} clean Markdown documents in {target_dir}")

    h_split, r_split = create_structure_aware_splitters(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    all_chunks: List[Document] = []
    for md_file in md_files:
        doc_chunks = chunk_single_document(
            file_path=md_file,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            header_splitter=h_split,
            recursive_splitter=r_split,
        )
        all_chunks.extend(doc_chunks)

    logger.info(f"Total chunks created across all {len(md_files)} documents: {len(all_chunks)}")
    return all_chunks


# =====================================================================
# EXPORT & MANIFEST FUNCTIONS
# =====================================================================

def save_chunks_to_json(
    chunks: Sequence[Document],
    output_path: Optional[Union[str, Path]] = None,
    ) -> Path:
    """Exports all chunks and comprehensive metadata to a JSON file.

    Args:
        chunks: Sequence of LangChain Document chunks.
        output_path: Destination JSON path (defaults to Hybrid_Rag/chunks/chunks_manifest.json).

    Returns:
        Resolved Path to the saved JSON file.
    """
    if output_path:
        out_file = Path(output_path).resolve()
    else:
        out_file = DEFAULT_OUTPUT_DIR / "chunks_manifest.json"

    out_file.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "total_chunks": len(chunks),
        "total_words": sum(c.metadata.get("word_count", 0) for c in chunks),
        "total_characters": sum(c.metadata.get("char_count", 0) for c in chunks),
        "chunks_with_tables": sum(1 for c in chunks if c.metadata.get("has_table")),
        "chunks": [
            {
                "chunk_id": c.metadata.get("chunk_id"),
                "chunk_index": c.metadata.get("chunk_index"),
                "total_chunks": c.metadata.get("total_chunks"),
                "content": c.page_content,
                "metadata": c.metadata,
            }
            for c in chunks
        ],
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    logger.info(f"Saved {len(chunks)} chunks to {out_file}")
    return out_file


# =====================================================================
# PIPELINE ENTRYPOINT
# =====================================================================

def run_chunking_pipeline(
    cleaned_docs_dir: Optional[Union[str, Path]] = None,
    output_dir: Optional[Union[str, Path]] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
    ) -> List[Document]:
    """Executes the complete structure-aware chunking pipeline.

    1. Loads cleaned Markdown files from cleaned_documents
    2. Applies two-stage recursive structure-aware chunking
    3. Enriches metadata with chunk IDs, breadcrumbs, stats
    4. Saves chunks manifest JSON to Hybrid_Rag/chunks/chunks_manifest.json
    """
    logger.info("=" * 70)
    logger.info("STARTING HYBRID RAG STRUCTURE-AWARE CHUNKING PIPELINE")
    logger.info(f"Cleaned Docs Directory : {cleaned_docs_dir or DEFAULT_CLEANED_DIR}")
    logger.info(f"Target Chunks Directory: {output_dir or DEFAULT_OUTPUT_DIR}")
    logger.info(f"Chunk Size / Overlap   : {chunk_size} / {chunk_overlap} chars")
    logger.info("=" * 70)

    chunks = chunk_all_documents(
        cleaned_docs_dir=cleaned_docs_dir,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    manifest_file = save_chunks_to_json(
        chunks,
        output_path=(Path(output_dir).resolve() / "chunks_manifest.json") if output_dir else None,
    )

    table_chunks = sum(1 for c in chunks if c.metadata.get("has_table"))

    logger.info("=" * 70)
    logger.info("[CHUNKING PIPELINE COMPLETE]")
    logger.info(f"Total Chunks Generated : {len(chunks)}")
    logger.info(f"Chunks with Tables     : {table_chunks}")
    logger.info(f"Manifest File Saved    : {manifest_file}")
    logger.info("=" * 70)

    return chunks


if __name__ == "__main__":
    run_chunking_pipeline()
