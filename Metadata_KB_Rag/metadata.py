"""
Metadata Schema & Enrichment Module for NexaCore Knowledge Base RAG (Project 2).

Defines the enterprise metadata schema, automated metadata inference, LlamaIndex
exclusion rules (excluded_embed_metadata_keys, excluded_llm_metadata_keys), and
citation label generators for grounded generation.
"""

import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union

try:
    from llama_index.core.schema import BaseNode, Document
except ImportError:
    class Document:  # type: ignore
        def __init__(self, text: str = "", metadata: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
            self.text = text
            self.metadata = metadata or {}
            self.doc_id = kwargs.get("doc_id", "")

    class BaseNode:  # type: ignore
        pass

logger = logging.getLogger(__name__)

# Mandatory schema keys expected in every LlamaIndex Document & Node
MANDATORY_METADATA_KEYS = {
    "file_name",
    "file_type",
    "department",
    "category",
    "source",
    "document_type",
    "doc_id",
}

# Metadata keys EXCLUDED from vector embeddings to prevent noise
DEFAULT_EXCLUDED_EMBED_KEYS = [
    "file_path",
    "size_bytes",
    "created_date",
    "modified_date",
    "char_count_before",
    "char_count_after",
    "char_reduction_percent",
    "doc_id",
]

# Metadata keys EXCLUDED from LLM prompt context to reduce prompt clutter
DEFAULT_EXCLUDED_LLM_KEYS = [
    "file_path",
    "size_bytes",
    "char_count_before",
    "char_count_after",
    "char_reduction_percent",
]


@dataclass
class NexaCoreMetadataSchema:
    """Standardized metadata dataclass for NexaCore Knowledge Base documents and nodes."""

    file_name: str
    file_type: str
    department: str
    category: str
    source: str
    document_type: str
    doc_id: str
    file_path: str
    size_bytes: int
    created_date: str
    modified_date: str
    page_number: int = 1
    total_pages: int = 1
    header_path: Optional[str] = None
    section: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata object to clean dictionary representation."""
        return {k: v for k, v in asdict(self).items() if v is not None}


def infer_document_type(file_name: str) -> str:
    """Infer semantic document_type classification based on file naming patterns.

    Args:
        file_name: Name of the target document file.

    Returns:
        String classification identifier.
    """
    fn = file_name.lower()
    if "handbook" in fn:
        return "employee_handbook"
    elif "policy" in fn or "leave" in fn or "remote" in fn:
        return "policy_document"
    elif "api" in fn or "standard" in fn or "schema" in fn or "architecture" in fn:
        return "technical_standard"
    elif "guide" in fn or "sop" in fn or "manual" in fn or "workflow" in fn or "deployment" in fn:
        return "operating_guide"
    elif "finance" in fn or "reimbursement" in fn or "budget" in fn or "payroll" in fn or "expense" in fn:
        return "financial_document"
    elif "security" in fn or "compliance" in fn or "audit" in fn or "incident" in fn or "access" in fn:
        return "security_compliance"
    else:
        return "general_document"


def build_metadata_extractor(base_dir: Path) -> Callable[[str], Dict[str, Any]]:
    """Build a metadata extraction callback function for LlamaIndex SimpleDirectoryReader.

    Args:
        base_dir: Root datasource path.

    Returns:
        Callable taking a file path string and returning a metadata payload dictionary.
    """
    resolved_base = base_dir.resolve()

    def extract_file_metadata(file_path_str: str) -> Dict[str, Any]:
        path = Path(file_path_str).resolve()
        ext = path.suffix.lstrip(".").lower()

        # Extract department from folder relative to datasource root
        try:
            rel_parts = path.relative_to(resolved_base).parts
            department = rel_parts[0] if len(rel_parts) > 1 else "general"
            source = path.relative_to(resolved_base).as_posix()
        except ValueError:
            department = path.parent.name or "general"
            source = path.name

        # Stat timestamps & file size
        try:
            stat = path.stat()
            size_bytes = stat.st_size
            created_dt = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            modified_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            size_bytes = 0
            created_dt = "Unknown"
            modified_dt = "Unknown"

        doc_type = infer_document_type(path.name)
        doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, path.name))

        metadata = NexaCoreMetadataSchema(
            file_name=path.name,
            file_type=ext,
            department=department,
            category=department,
            source=source,
            document_type=doc_type,
            doc_id=doc_id,
            file_path=str(path),
            size_bytes=size_bytes,
            created_date=created_dt,
            modified_date=modified_dt,
        ).to_dict()

        return metadata

    return extract_file_metadata


def configure_llamaindex_metadata_exclusions(
    node: Any,
    excluded_embed_keys: Optional[List[str]] = None,
    excluded_llm_keys: Optional[List[str]] = None,
) -> Any:
    """Configure excluded metadata keys on a LlamaIndex Document or Node instance."""
    embed_keys = excluded_embed_keys if excluded_embed_keys is not None else DEFAULT_EXCLUDED_EMBED_KEYS
    llm_keys = excluded_llm_keys if excluded_llm_keys is not None else DEFAULT_EXCLUDED_LLM_KEYS

    if hasattr(node, "excluded_embed_metadata_keys"):
        node.excluded_embed_metadata_keys = list(set(getattr(node, "excluded_embed_metadata_keys", []) + embed_keys))
    if hasattr(node, "excluded_llm_metadata_keys"):
        node.excluded_llm_metadata_keys = list(set(getattr(node, "excluded_llm_metadata_keys", []) + llm_keys))

    return node


def format_citation_label(metadata: Dict[str, Any]) -> str:
    """Format a standardized citation string for Gemini LLM response grounding.

    Args:
        metadata: Metadata dictionary of a retrieved node/document.

    Returns:
        Formatted citation label string.
    """
    file_name = metadata.get("file_name", "Unknown Source")
    department = metadata.get("department", "General").upper()
    page = metadata.get("page_number", 1)
    section = metadata.get("section") or metadata.get("header_path")

    citation = f"[Source: {file_name} | Dept: {department} | Page: {page}"
    if section:
        citation += f" | Section: {section}"
    citation += "]"
    return citation


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    sample_meta = {
        "file_name": "employee_handbook.pdf",
        "department": "hr",
        "page_number": 3,
        "section": "Casual Leave Policy",
    }
    print("Sample Citation Format:")
    print(format_citation_label(sample_meta))
