"""Document Cleaner & Exporter Module (Functional Approach).

Provides pure, standalone functions to clean, normalize, metadata-enrich,
and export LangChain Document objects into structure-aware Markdown documents
with standard YAML frontmatter into a dynamically configured cleaned_documents folder.
"""

import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Union

# LangChain Document representation
from langchain_core.documents import Document

# Functional loader & parser imports
from document_loader import DEFAULT_SOURCE_DIR, PROJECT_ROOT, load_all_documents
from document_parser import clean_stem_name

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("document_cleaner")

# Dynamic output directory resolution (independent of hardcoded drive paths)
DEFAULT_OUTPUT_DIR = Path(os.getenv("RAG_OUTPUT_DIR", str(PROJECT_ROOT / "cleaned_documents")))


def get_default_output_dir() -> Path:
    """Returns the dynamically resolved default output directory."""
    return DEFAULT_OUTPUT_DIR

# verified
def clean_text(text: str) -> str:
    """Cleans raw text with zero information loss.

    - Normalizes line endings (\\r\\n -> \\n)
    - Normalizes unicode spaces (\\xa0 -> ' ') and strips invisible chars
    - Strips non-printable ASCII control characters (preserving \\n, \\t)
    - Trims trailing whitespace per line while preserving indentation & table structure
    - Collapses excessive runs of blank lines down to 2
    """
    if not text:
        return ""

    # 1. Line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Unicode artifacts & zero-width characters
    text = text.replace("\xa0", " ").replace("\u200b", "").replace("\xad", "")

    # 3. Non-printable control characters
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

    # 4. Trim trailing line whitespace while preserving markdown indentation
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    # 5. Limit runs of 4+ newlines to 2 empty lines
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    return text.strip()

# verified
def infer_document_type(file_name: str, file_type: str, category: str) -> str:
    """Infers high-level semantic document classification."""
    fn = file_name.lower()
    if "handbook" in fn:
        return "handbook"
    elif "policy" in fn or "rules" in fn:
        return "policy"
    elif "guide" in fn or "guidelines" in fn or "standards" in fn:
        return "guideline"
    elif "playbook" in fn:
        return "playbook"
    elif "catalog" in fn:
        return "catalog"
    elif file_type in (".xlsx", ".xls"):
        return "spreadsheet"
    elif file_type in (".pptx", ".ppt"):
        return "presentation"
    elif file_type == ".pdf":
        return "pdf_document"
    else:
        return "text_document"

# verified
def build_yaml_frontmatter(metadata: Dict[str, Any]) -> str:
    """Generates standard YAML Frontmatter string for Markdown documents."""
    lines = [
        "---",
        f'title: "{metadata.get("title", "")}"',
        f'original_file: "{metadata.get("file_name", "")}"',
        f'category: "{metadata.get("category", "")}"',
        f'document_type: "{metadata.get("document_type", "")}"',
        f'source_path: "{metadata.get("source", "")}"',
        f'total_words: {metadata.get("total_words", 0)}',
        f'total_chars: {metadata.get("total_chars", 0)}',
        f'has_tables: {str(metadata.get("has_tables", False)).lower()}',
        f'table_count: {metadata.get("table_count", 0)}',
        "---",
        "",
        f"> **Location:** {metadata.get('breadcrumbs', '')}",
        "",
    ]
    return "\n".join(lines)

# verified
def clean_single_document(doc: Document) -> Document:
    """Cleans text, computes word/character statistics, enriches metadata,

    and prepends standard YAML frontmatter to the LangChain Document.
    """
    raw_text = doc.page_content or ""
    cleaned = clean_text(raw_text)

    words = len(cleaned.split())
    chars = len(cleaned)
    meta = dict(doc.metadata)

    file_name = meta.get("file_name", "")
    file_type = meta.get("file_type", "")
    category = meta.get("category", "")

    doc_type = infer_document_type(file_name, file_type, category)
    title = clean_stem_name(Path(file_name).stem).replace("_", " ").title()

    meta.update({
        "title": title,
        "document_type": doc_type,
        "total_words": words,
        "total_chars": chars,
        "estimated_reading_minutes": round(words / 200, 1),
    })

    frontmatter = build_yaml_frontmatter(meta)
    header_h1 = f"# {title}\n\n" if not cleaned.lstrip().startswith("#") else ""
    full_markdown = f"{frontmatter}\n{header_h1}{cleaned}\n"

    return Document(page_content=full_markdown, metadata=meta)

# verified
def clean_all_documents(documents: Sequence[Document]) -> List[Document]:
    """Cleans and enriches a list of LangChain Document objects."""
    logger.info(f"Cleaning and normalizing {len(documents)} documents...")
    return [clean_single_document(doc) for doc in documents]


# verified
def export_cleaned_documents(
    documents: Sequence[Document],
    output_dir: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
    """Exports cleaned LangChain documents to disk in departmental folders

    and creates a dataset manifest summary dynamically.
    """
    target_dir = Path(output_dir).resolve() if output_dir else DEFAULT_OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest_entries: List[Dict[str, Any]] = []

    logger.info(f"Exporting {len(documents)} clean Markdown documents to {target_dir}...")

    for doc in documents:
        meta = doc.metadata
        category = meta.get("category", "general")
        clean_name = meta.get("clean_name", f"{clean_stem_name(Path(meta.get('file_name', 'doc')).stem)}.md")

        dept_folder = target_dir / category
        dept_folder.mkdir(parents=True, exist_ok=True)
        out_file = dept_folder / clean_name

        with open(out_file, "w", encoding="utf-8") as f:
            f.write(doc.page_content)

        manifest_entries.append({
            "clean_file": f"{category}/{clean_name}",
            "absolute_path": str(out_file),
            "original_file": meta.get("file_name"),
            "source_path": meta.get("source"),
            "category": category,
            "document_type": meta.get("document_type"),
            "total_words": meta.get("total_words"),
            "total_chars": meta.get("total_chars"),
            "has_tables": meta.get("has_tables"),
            "table_count": meta.get("table_count"),
            "metadata": meta,
        })

    manifest_path = target_dir / "cleaned_documents_manifest.json"
    manifest_data = {
        "total_documents": len(documents),
        "total_words": sum(e["total_words"] for e in manifest_entries),
        "total_characters": sum(e["total_chars"] for e in manifest_entries),
        "total_tables": sum(e["table_count"] for e in manifest_entries),
        "documents": manifest_entries,
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    logger.info(f"Successfully exported {len(documents)} files and manifest to {target_dir}")
    return manifest_data


def run_pipeline(
    source_dir: Optional[Union[str, Path]] = None,
    output_dir: Optional[Union[str, Path]] = None,
    max_workers: int = 4,
    ) -> Dict[str, Any]:
    """End-to-end procedural pipeline using dynamic path defaults:

    1. Discovers & loads all files dynamically into LangChain Documents
    2. Cleans text, preserves tables, enriches metadata & frontmatter
    3. Exports clean Markdown documents and manifest to output directory
    """
    src_path = Path(source_dir).resolve() if source_dir else DEFAULT_SOURCE_DIR
    out_path = Path(output_dir).resolve() if output_dir else DEFAULT_OUTPUT_DIR

    logger.info("=" * 70)
    logger.info("EXECUTING FUNCTIONAL DATA PIPELINE FOR HYBRID RAG")
    logger.info(f"Source: {src_path} | Output: {out_path}")
    logger.info("=" * 70)

    # 1. Load
    docs = load_all_documents(source_dir=src_path, parallel=True, max_workers=max_workers)

    # 2. Clean & Enrich
    cleaned_docs = clean_all_documents(docs)

    # 3. Export
    summary = export_cleaned_documents(cleaned_docs, output_dir=out_path)

    logger.info("=" * 70)
    logger.info("[PIPELINE COMPLETE]")
    logger.info(f"Processed Documents: {summary['total_documents']}")
    logger.info(f"Total Words: {summary['total_words']:,}")
    logger.info(f"Total Tables Formatted: {summary['total_tables']}")
    logger.info("=" * 70)

    return summary


if __name__ == "__main__":
    run_pipeline()
