"""
Document Loader Module for NexaCore Knowledge Base RAG (Project 2).

Pure LlamaIndex implementation utilizing SimpleDirectoryReader and file_metadata callbacks
to discover, parse, and load documents into standard LlamaIndex Document instances.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from llama_index.core import Document, SimpleDirectoryReader
from llama_index.readers.file import DocxReader, MarkdownReader, PyMuPDFReader

logger = logging.getLogger(__name__)

# Allowed file extensions for Project 2
SUPPORTED_EXTENSIONS: Set[str] = {".pdf", ".docx", ".md", ".txt"}

# Explicitly excluded extensions
EXCLUDED_EXTENSIONS: Set[str] = {".xlsx", ".pptx", ".json"}

DEFAULT_DATASOURCE_DIR = Path(__file__).resolve().parent.parent / "Datasource"


@dataclass
class DiscoveredFile:
    """Dataclass holding discovered file metadata for summary reporting."""
    file_path: Path
    file_name: str
    file_type: str
    category: str
    department: str
    source: str
    size_bytes: int
    created_date: str
    modified_date: str

    def to_metadata_dict(self) -> Dict[str, Union[str, int]]:
        """Convert metadata attributes into a clean dictionary."""
        return {
            "file_name": self.file_name,
            "file_type": self.file_type,
            "category": self.category,
            "department": self.department,
            "source": self.source,
            "file_path": str(self.file_path),
            "size_bytes": self.size_bytes,
            "created_date": self.created_date,
            "modified_date": self.modified_date,
        }


class DocumentLoader:
    """Pure LlamaIndex Document Loader leveraging SimpleDirectoryReader and file_metadata callbacks."""

    def __init__(self, datasource_dir: Optional[Union[str, Path]] = None):
        self.datasource_dir = Path(datasource_dir if datasource_dir is not None else DEFAULT_DATASOURCE_DIR).resolve()
        logger.info(f"Initialized LlamaIndex DocumentLoader targeting: '{self.datasource_dir}'")

    def extract_file_metadata(self, file_path_str: str) -> Dict[str, Union[str, int]]:
        """LlamaIndex metadata extractor callback attached to SimpleDirectoryReader."""
        try:
            from metadata import build_metadata_extractor
            extractor = build_metadata_extractor(self.datasource_dir)
            return extractor(file_path_str)
        except ImportError:
            path = Path(file_path_str)
            try:
                rel_path = path.relative_to(self.datasource_dir)
                department = rel_path.parts[0] if len(rel_path.parts) > 1 else "general"
                source = rel_path.as_posix()
            except ValueError:
                department = "general"
                source = path.name

            stat = path.stat()
            created_dt = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            modified_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            return {
                "file_name": path.name,
                "file_type": path.suffix.lstrip(".").lower(),
                "category": department,
                "department": department,
                "source": source,
                "file_path": str(path),
                "size_bytes": stat.st_size,
                "created_date": created_dt,
                "modified_date": modified_dt,
            }

    def load_documents(self) -> List[Document]:
        """Load all target files directly as LlamaIndex Document instances via SimpleDirectoryReader."""
        if not self.datasource_dir.exists():
            raise FileNotFoundError(f"Datasource directory does not exist: {self.datasource_dir}")

        # Use structure-aware custom readers for .pdf (pymupdf4llm) and .docx (python-docx markdown tables)
        # Note: .md and .txt use SimpleDirectoryReader's default FlatReader to ingest full content with 0% data loss
        try:
            from document_parser import get_custom_file_extractors
            file_extractor = get_custom_file_extractors()
        except ImportError:
            file_extractor = None

        # Initialize LlamaIndex SimpleDirectoryReader
        reader = SimpleDirectoryReader(
            input_dir=str(self.datasource_dir),
            recursive=True,
            required_exts=list(SUPPORTED_EXTENSIONS),
            file_metadata=self.extract_file_metadata,
            file_extractor=file_extractor,
        )

        documents = reader.load_data()

        # Configure LlamaIndex embedding and LLM metadata exclusions
        try:
            from metadata import configure_llamaindex_metadata_exclusions
            for doc in documents:
                configure_llamaindex_metadata_exclusions(doc)
        except ImportError:
            pass

        logger.info(f"Loaded {len(documents)} LlamaIndex Document(s) via SimpleDirectoryReader with configured metadata exclusions.")
        return documents

    def discover_files(self) -> List[DiscoveredFile]:
        """Discover target files for reporting compatibility."""
        if not self.datasource_dir.exists():
            raise FileNotFoundError(f"Datasource directory does not exist: {self.datasource_dir}")

        discovered: List[DiscoveredFile] = []
        for path in sorted(self.datasource_dir.rglob("*")):
            if not path.is_file():
                continue

            ext = path.suffix.lower()
            if ext in EXCLUDED_EXTENSIONS or ext not in SUPPORTED_EXTENSIONS:
                continue

            meta = self.extract_file_metadata(str(path))
            file_record = DiscoveredFile(
                file_path=path,
                file_name=meta["file_name"],
                file_type=meta["file_type"],
                category=meta["category"],
                department=meta["department"],
                source=meta["source"],
                size_bytes=meta["size_bytes"],
                created_date=meta["created_date"],
                modified_date=meta["modified_date"],
            )
            discovered.append(file_record)

        return discovered


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    loader = DocumentLoader()
    documents = loader.load_documents()

    print("\n" + "=" * 80)
    print(f" LLAMAINDEX SIMPLEDIRECTORYREADER LOADED ({len(documents)} total Document objects)")
    print("=" * 80)
    for doc in documents[:5]:
        print(f" - [ID: {doc.doc_id[:12]}...] {doc.metadata.get('source')} | Dept: {doc.metadata.get('department')}")
        print(f"   Snippet: {doc.text[:120]}...\n")
