"""
Document Loader Module for NexaCore Semantic Document Search.

Discovers and loads PDF documents from a specified datasource directory
using PyMuPDF (fitz), preserving file paths and category metadata.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

import pymupdf as fitz

logger = logging.getLogger(__name__)


@dataclass
class LoadedPDF:
    """Dataclass holding a loaded PyMuPDF Document with metadata."""
    doc: fitz.Document
    file_path: Path
    filename: str
    category: str
    page_count: int

    def close(self):
        """Close the underlying PyMuPDF document handle."""
        if self.doc and not self.doc.is_closed:
            self.doc.close()


DEFAULT_DATASOURCE_DIR = Path(__file__).resolve().parent.parent / "Datasource"


class PDFDocumentLoader:
    """Discovers and loads PDF files from a target directory."""

    def __init__(self, datasource_dir: Optional[Union[str, Path]] = None):
        self.datasource_dir = Path(datasource_dir if datasource_dir is not None else DEFAULT_DATASOURCE_DIR).resolve()

    def discover_pdf_files(self) -> List[Path]:
        """Scan the datasource directory recursively for .pdf files."""
        if not self.datasource_dir.exists():
            raise FileNotFoundError(f"Datasource directory not found: {self.datasource_dir}")

        pdf_files = list(self.datasource_dir.rglob("*.pdf"))
        logger.info(f"Discovered {len(pdf_files)} PDF file(s) in {self.datasource_dir}")
        return pdf_files

    def load_pdf(self, file_path: Path) -> Optional[LoadedPDF]:
        """Load a single PDF file using PyMuPDF."""
        try:
            doc = fitz.open(file_path)
            category = file_path.parent.name if file_path.parent != self.datasource_dir else "general"
            loaded_pdf = LoadedPDF(
                doc=doc,
                file_path=file_path,
                filename=file_path.name,
                category=category,
                page_count=doc.page_count,
            )
            logger.info(f"Successfully loaded '{file_path.name}' ({doc.page_count} pages) [Category: {category}]")
            return loaded_pdf
        except Exception as e:
            logger.error(f"Failed to load PDF '{file_path}': {e}")
            return None

    def load_all_pdfs(self) -> List[LoadedPDF]:
        """Discover and load all PDF files in the datasource directory."""
        pdf_files = self.discover_pdf_files()
        loaded_documents: List[LoadedPDF] = []
        for file_path in pdf_files:
            loaded = self.load_pdf(file_path)
            if loaded:
                loaded_documents.append(loaded)
        return loaded_documents


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loader = PDFDocumentLoader()
    docs = loader.load_all_pdfs()
    print(f"\nLoaded total {len(docs)} PDF documents.")
    for d in docs:
        print(f" - {d.filename} | Category: {d.category} | Pages: {d.page_count}")
        d.close()
