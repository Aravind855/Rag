"""
Document Parsing Module for NexaCore Semantic Document Search.

Extracts text content page-by-page from loaded PDF objects, creating
structured representations containing text, page numbers, and source metadata.
"""

import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List

from document_loader import LoadedPDF, PDFDocumentLoader

logger = logging.getLogger(__name__)


@dataclass
class ParsedPage:
    """Structured representation of a parsed PDF page."""
    text: str
    page_number: int
    total_pages: int
    source_file: str
    file_path: str
    category: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert page metadata into a plain dictionary."""
        return asdict(self)


class PDFDocumentParser:
    """Parses PyMuPDF document handles into structured page records."""

    def parse_document(self, loaded_pdf: LoadedPDF) -> List[ParsedPage]:
        """Extract text page-by-page from a single loaded PDF document."""
        parsed_pages: List[ParsedPage] = []
        doc = loaded_pdf.doc

        for page_idx in range(loaded_pdf.page_count):
            try:
                page = doc.load_page(page_idx)
                raw_text = page.get_text("text")
                
                parsed_page = ParsedPage(
                    text=raw_text,
                    page_number=page_idx + 1,  # 1-indexed
                    total_pages=loaded_pdf.page_count,
                    source_file=loaded_pdf.filename,
                    file_path=str(loaded_pdf.file_path),
                    category=loaded_pdf.category,
                )
                parsed_pages.append(parsed_page)
            except Exception as e:
                logger.error(
                    f"Error parsing page {page_idx + 1} of '{loaded_pdf.filename}': {e}"
                )

        logger.info(
            f"Parsed {len(parsed_pages)} page(s) from '{loaded_pdf.filename}'"
        )
        return parsed_pages

    def parse_all_documents(self, loaded_pdfs: List[LoadedPDF]) -> List[ParsedPage]:
        """Parse multiple loaded PDF documents into a flat list of ParsedPage objects."""
        all_parsed_pages: List[ParsedPage] = []
        for pdf in loaded_pdfs:
            pages = self.parse_document(pdf)
            all_parsed_pages.extend(pages)
        logger.info(f"Total parsed pages across all documents: {len(all_parsed_pages)}")
        return all_parsed_pages


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loader = PDFDocumentLoader()
    parser = PDFDocumentParser()

    loaded_pdfs = loader.load_all_pdfs()
    parsed_pages = parser.parse_all_documents(loaded_pdfs)

    print(f"\nExtracted {len(parsed_pages)} total page records.")
    if parsed_pages:
        sample = parsed_pages[0]
        print(f"\n--- Sample Parsed Page (Source: {sample.source_file}, Page {sample.page_number}/{sample.total_pages}) ---")
        print(sample.text[:300] + "...")

    for pdf in loaded_pdfs:
        pdf.close()
