"""Document Loader Module (Functional Approach).

Provides pure, standalone functions to dynamically discover and load
multi-format files from any source directory into standardized
LangChain Document objects without hardcoded paths or class-based abstractions.
"""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# LangChain Document representation
from langchain_core.documents import Document

# Functional parser import
from document_parser import parse_document

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("document_loader")

# Dynamic root resolution (independent of execution working directory or hardcoded drive paths)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_DIR = Path(os.getenv("RAG_SOURCE_DIR", str(PROJECT_ROOT / "Datasource")))


def get_default_source_dir() -> Path:
    """Returns the dynamically resolved default source directory."""
    return DEFAULT_SOURCE_DIR

# verified
def discover_files(source_dir: Optional[Union[str, Path]] = None) -> List[Tuple[Path, Dict[str, Any]]]:
    """Recursively scans target directory to discover processable files.

    Args:
        source_dir: Directory path to scan (defaults dynamically to PROJECT_ROOT / 'Datasource').

    Returns:
        List of tuples (file_path, metadata_dict).
    """
    root_dir = Path(source_dir).resolve() if source_dir else DEFAULT_SOURCE_DIR
    if not root_dir.exists():
        logger.error(f"Source directory does not exist: {root_dir}")
        return []

    discovered: List[Tuple[Path, Dict[str, Any]]] = []

    for item in sorted(root_dir.rglob("*")):
        if not item.is_file():
            continue
        if item.name.startswith(".") or item.name.startswith("~$") or item.name == "readme.md":
            continue

        try:
            rel_path = item.relative_to(root_dir)
            parts = rel_path.parts
            subfolders = list(parts[:-1]) if len(parts) > 1 else []
            category = "/".join(subfolders) if subfolders else "root"
        except ValueError:
            subfolders = []
            category = "general"

        file_info = {
            "category": category,
            "relative_path": str(rel_path).replace("\\", "/"),
            "subfolders": subfolders,
            "file_size_bytes": item.stat().st_size if item.exists() else 0,
            "extension": item.suffix.lower() or "no_extension",
        }
        discovered.append((item, file_info))

    logger.info(f"Discovered {len(discovered)} files dynamically in {root_dir}")
    return discovered

# verified
def load_single_document(file_path: Union[str, Path], file_info: Optional[Dict[str, Any]] = None) -> Document:
    """Loads and parses a single document into a LangChain Document.

    Args:
        file_path: Path to document file.
        file_info: Optional precomputed metadata dictionary.

    Returns:
        LangChain Document instance.
    """
    path = Path(file_path).resolve()
    info = file_info or {"category": "general", "relative_path": path.name, "subfolders": []}
    category = info.get("category", "general")

    doc = parse_document(path, category=category)
    doc.metadata.update({
        "source": info.get("relative_path", path.name),
        "relative_path": info.get("relative_path", path.name),
        "subfolders": info.get("subfolders", []),
        "file_size_bytes": info.get("file_size_bytes", 0),
    })

    return doc

# verified
def load_all_documents(
    source_dir: Optional[Union[str, Path]] = None,
    parallel: bool = True,
    max_workers: int = 4,
    ) -> List[Document]:
    """Loads and parses all discovered documents dynamically.

    Args:
        source_dir: Directory path to scan (defaults dynamically to PROJECT_ROOT / 'Datasource').
        parallel: Whether to use multithreading for concurrent file loading.
        max_workers: Maximum worker threads.

    Returns:
        List of LangChain Document objects.
    """
    target_source = Path(source_dir).resolve() if source_dir else DEFAULT_SOURCE_DIR
    files_to_process = discover_files(target_source)
    if not files_to_process:
        logger.warning(f"No processable files found in {target_source}.")
        return []

    start_time = time.time()
    results: List[Document] = []

    if parallel and len(files_to_process) > 1:
        logger.info(f"Loading {len(files_to_process)} documents concurrently with {max_workers} threads...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(load_single_document, file_path, file_info): (file_path, file_info)
                for file_path, file_info in files_to_process
            }
            for future in as_completed(future_to_file):
                file_path, file_info = future_to_file[future]
                try:
                    doc = future.result()
                    results.append(doc)
                except Exception as e:
                    logger.error(f"Error loading {file_path.name}: {e}")
                    results.append(
                        Document(
                            page_content="",
                            metadata={
                                "file_name": file_path.name,
                                "source": file_info.get("relative_path", file_path.name),
                                "category": file_info.get("category", "general"),
                                "error": str(e),
                            },
                        )
                    )
    else:
        for file_path, file_info in files_to_process:
            try:
                doc = load_single_document(file_path, file_info)
                results.append(doc)
            except Exception as e:
                logger.error(f"Error loading {file_path.name}: {e}")

    elapsed = round(time.time() - start_time, 2)
    logger.info(f"Loaded {len(results)} documents successfully in {elapsed}s.")
    return results


if __name__ == "__main__":
    print(f"Testing dynamic document_loader from: {DEFAULT_SOURCE_DIR}")
    docs = load_all_documents(parallel=True)
    print(f"Total documents loaded: {len(docs)}")
    for d in docs[:3]:
        print(f" - [{d.metadata.get('category')}] {d.metadata.get('file_name')} ({len(d.page_content)} chars)")
