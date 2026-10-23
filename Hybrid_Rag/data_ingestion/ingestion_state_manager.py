"""Ingestion State & Cryptographic Hash Manager (Functional Approach).

Maintains a durable, atomic manifest of all ingested files in the RAG pipeline.
Tracks file versions, SHA-256 byte hashes, content hashes, modification timestamps,
and processing dispositions to enable zero-compute incremental ingestion.

Strictly procedural (zero classes). All paths resolved dynamically.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ingestion_state_manager")

# Dynamic Root Resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_STATE_FILE = PROJECT_ROOT / "cleaned_documents" / "ingestion_state.json"


def get_default_state_file() -> Path:
    """Returns the dynamically resolved path to the ingestion state file."""
    env_path = os.getenv("RAG_INGESTION_STATE_PATH")
    if env_path:
        return Path(env_path).resolve()
    return DEFAULT_STATE_FILE


def compute_file_sha256(file_path: Union[str, Path]) -> str:
    """Computes SHA-256 hash of raw file bytes using chunked streaming."""
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Cannot compute hash for non-existent file: {path}")

    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_content_sha256(content: str) -> str:
    """Computes SHA-256 hash of extracted text/markdown content."""
    hasher = hashlib.sha256()
    hasher.update(content.encode("utf-8", errors="replace"))
    return hasher.hexdigest()


def load_ingestion_state(state_file: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Loads durable ingestion state JSON. Returns a fresh state template if missing."""
    target_path = Path(state_file).resolve() if state_file else get_default_state_file()

    if target_path.exists():
        try:
            content = target_path.read_text(encoding="utf-8")
            data = json.loads(content)
            if isinstance(data, dict) and "entries" in data:
                return data
        except Exception as e:
            logger.warning(f"Error reading state file {target_path}, initializing new state: {e}")

    # Fresh state template
    return {
        "version": "1.0",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_active_files": 0,
        "entries": {},
    }


def save_ingestion_state(state: Dict[str, Any], state_file: Optional[Union[str, Path]] = None) -> None:
    """Atomically persists ingestion state to disk."""
    target_path = Path(state_file).resolve() if state_file else get_default_state_file()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    state["total_active_files"] = len(state.get("entries", {}))

    temp_path = target_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temp_path.replace(target_path)
    logger.debug(f"Saved ingestion state ({state['total_active_files']} active entries) to {target_path}")


def generate_file_id(source_rel_path: str) -> str:
    """Generates a stable, canonical file identifier from relative path."""
    clean = source_rel_path.replace("\\", "/").lower().strip("/")
    return re.sub(r"[^a-z0-9]+", "_", clean).strip("_")


def detect_catalog_changes(
    source_dir: Path,
    state: Dict[str, Any]
) -> Dict[str, Any]:
    """Inspects raw datasource files against stored state to detect changes.

    Returns:
        Dict with keys:
            - 'new_files': List of (Path, metadata_dict)
            - 'modified_files': List of (Path, metadata_dict)
            - 'unchanged_files': List of Path
            - 'deleted_entries': List of str (source_rel_path)
    """
    entries = state.get("entries", {})
    existing_keys: Set[str] = set(entries.keys())
    seen_keys: Set[str] = set()

    new_files: List[Tuple[Path, Dict[str, Any]]] = []
    modified_files: List[Tuple[Path, Dict[str, Any]]] = []
    unchanged_files: List[Path] = []

    # Recursively find all files in source directory
    for item in sorted(source_dir.rglob("*")):
        if not item.is_file():
            continue
        if item.name.startswith(".") or item.name.startswith("~$") or item.name == "readme.md":
            continue

        try:
            rel_path = str(item.relative_to(source_dir)).replace("\\", "/")
        except ValueError:
            rel_path = item.name

        seen_keys.add(rel_path)
        stat = item.stat()
        current_mtime = stat.st_mtime
        current_size = stat.st_size

        entry = entries.get(rel_path)

        # Determine category from relative subfolder
        parts = Path(rel_path).parts
        category = parts[0] if len(parts) > 1 else "general"

        if not entry:
            # Entirely new file
            current_hash = compute_file_sha256(item)
            file_meta = {
                "source_path": rel_path,
                "file_name": item.name,
                "category": category,
                "file_size_bytes": current_size,
                "mtime": current_mtime,
                "sha256": current_hash,
                "extension": item.suffix.lower(),
            }
            new_files.append((item, file_meta))
        else:
            # Fast mtime & size check before computing full hash
            if entry.get("file_size_bytes") == current_size and entry.get("mtime") == current_mtime:
                unchanged_files.append(item)
            else:
                current_hash = compute_file_sha256(item)
                if current_hash == entry.get("sha256"):
                    # Unchanged content despite touched mtime
                    entry["mtime"] = current_mtime
                    unchanged_files.append(item)
                else:
                    file_meta = {
                        "source_path": rel_path,
                        "file_name": item.name,
                        "category": category,
                        "file_size_bytes": current_size,
                        "mtime": current_mtime,
                        "sha256": current_hash,
                        "extension": item.suffix.lower(),
                    }
                    modified_files.append((item, file_meta))

    deleted_entries = list(existing_keys - seen_keys)

    return {
        "new_files": new_files,
        "modified_files": modified_files,
        "unchanged_files": unchanged_files,
        "deleted_entries": deleted_entries,
        "total_source_files": len(new_files) + len(modified_files) + len(unchanged_files),
    }


def record_document_disposition(
    state: Dict[str, Any],
    source_rel_path: str,
    file_sha256: str,
    content_sha256: str,
    disposition: str,
    quality_score: float,
    validation_reasons: List[str],
    clean_file_rel: Optional[str] = None,
    error_message: Optional[str] = None
) -> None:
    """Updates the state record for a single processed document."""
    entries = state.setdefault("entries", {})
    entry = entries.get(source_rel_path, {})

    history = entry.get("version_history", [])
    history.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "disposition": disposition,
        "sha256": file_sha256,
        "quality_score": quality_score,
    })

    entries[source_rel_path] = {
        "file_id": generate_file_id(source_rel_path),
        "source_path": source_rel_path,
        "clean_file": clean_file_rel,
        "sha256": file_sha256,
        "content_sha256": content_sha256,
        "disposition": disposition,
        "quality_score": quality_score,
        "validation_reasons": validation_reasons,
        "error_message": error_message,
        "last_processed_at": datetime.now(timezone.utc).isoformat(),
        "version_count": len(history),
        "version_history": history[-5:],  # Keep last 5 versions
    }
