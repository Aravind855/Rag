"""
Document Loader Module for NexaCore Knowledge Base RAG (Project 2).

Discovers documents from the target datasource directory, strictly filters for
supported file extensions (.pdf, .docx, .md, .txt), ignores unsupported extensions
(.xlsx, .pptx, .json), and builds initial file-level metadata records.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)

# Allowed file extensions for Project 2
SUPPORTED_EXTENSIONS: Set[str] = {".pdf", ".docx", ".md", ".txt"}

# Explicitly excluded extensions (reserved for future projects)
EXCLUDED_EXTENSIONS: Set[str] = {".xlsx", ".pptx", ".json"}

DEFAULT_DATASOURCE_DIR = Path(__file__).resolve().parent.parent / "Datasource"


@dataclass
class DiscoveredFile:
    """Dataclass holding discovered file information and file-level metadata."""
    file_path: Path
    file_name: str
    file_type: str
    category: str
    size_bytes: int
    created_date: str
    modified_date: str

    def to_metadata_dict(self) -> Dict[str, Union[str, int]]:
        """Convert metadata attributes into a clean dictionary."""
        return {
            "file_name": self.file_name,
            "file_type": self.file_type,
            "category": self.category,
            "file_path": str(self.file_path),
            "size_bytes": self.size_bytes,
            "created_date": self.created_date,
            "modified_date": self.modified_date,
        }


class DocumentLoader:
    """Discovers and filters target documents from a datasource directory."""

    def __init__(self, datasource_dir: Optional[Union[str, Path]] = None):
        self.datasource_dir = Path(datasource_dir if datasource_dir is not None else DEFAULT_DATASOURCE_DIR).resolve()
        logger.info(f"Initialized DocumentLoader targeting: '{self.datasource_dir}'")

    def discover_files(self) -> List[DiscoveredFile]:
        """Scan datasource recursively, filtering for supported extensions (.pdf, .docx, .md, .txt)."""
        if not self.datasource_dir.exists():
            raise FileNotFoundError(f"Datasource directory does not exist: {self.datasource_dir}")

        discovered: List[DiscoveredFile] = []
        skipped_count = 0

        for path in sorted(self.datasource_dir.rglob("*")):
            if not path.is_file():
                continue

            ext = path.suffix.lower()

            if ext in EXCLUDED_EXTENSIONS:
                logger.debug(f"Skipping excluded file format ({ext}): '{path.name}'")
                skipped_count += 1
                continue

            if ext not in SUPPORTED_EXTENSIONS:
                logger.debug(f"Skipping unsupported file extension ({ext}): '{path.name}'")
                skipped_count += 1
                continue

            # Determine document category from subfolder name (e.g. hr, engineering, finance)
            relative_path = path.relative_to(self.datasource_dir)
            category = relative_path.parts[0] if len(relative_path.parts) > 1 else "general"

            # Get stat timestamps
            stat = path.stat()
            created_dt = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            modified_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            file_record = DiscoveredFile(
                file_path=path,
                file_name=path.name,
                file_type=ext.lstrip("."),
                category=category,
                size_bytes=stat.st_size,
                created_date=created_dt,
                modified_date=modified_dt,
            )
            discovered.append(file_record)
            logger.info(f"Discovered [{ext.upper()}] '{path.name}' (Category: '{category}')")

        logger.info(
            f"Discovery complete: Found {len(discovered)} supported file(s) across {self.datasource_dir.name}. "
            f"Skipped {skipped_count} unsupported file(s)."
        )
        return discovered


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    loader = DocumentLoader()
    files = loader.discover_files()

    print("\n" + "=" * 80)
    print(f" DISCOVERED FILES SUMMARY ({len(files)} total)")
    print("=" * 80)
    for f in files:
        print(f" - [{f.file_type.upper():<4}] {f.file_name:<30} | Category: {f.category:<12} | Size: {f.size_bytes:,} bytes")
