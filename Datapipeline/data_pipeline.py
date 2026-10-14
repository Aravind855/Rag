"""LangChain Pipeline Entrypoint (Functional Approach).

Orchestrates the data pipeline using pure procedural functions:
`load_all_documents() -> clean_all_documents() -> export_cleaned_documents()`
Paths are dynamically resolved from PROJECT_ROOT or environment variables.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from document_cleaner import clean_all_documents, export_cleaned_documents
from document_loader import DEFAULT_SOURCE_DIR, PROJECT_ROOT, load_all_documents

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("langchain_pipeline")

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "cleaned_documents"


def run_datapipeline(
    source_dir: Optional[Union[str, Path]] = None,
    output_dir: Optional[Union[str, Path]] = None,
    max_workers: int = 4,
    ) -> Dict[str, Any]:
    """Runs functional pipeline: Load -> Clean -> Enrich -> Export Markdown with dynamic paths."""
    src = Path(source_dir).resolve() if source_dir else DEFAULT_SOURCE_DIR
    out = Path(output_dir).resolve() if output_dir else DEFAULT_OUTPUT_DIR

    logger.info(f"Executing Functional LangChain Pipeline: {src} -> {out}")
    docs = load_all_documents(source_dir=src, parallel=True, max_workers=max_workers)
    cleaned_docs = clean_all_documents(docs)
    summary = export_cleaned_documents(cleaned_docs, output_dir=out)
    return summary


if __name__ == "__main__":
    run_datapipeline()
