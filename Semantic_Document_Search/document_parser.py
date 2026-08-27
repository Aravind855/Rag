"""
Structure-Preserving Document Parsing Module for NexaCore Semantic Document Search.

Extracts text, headings, subheadings, bullet lists, and tables as clean Markdown
from PDF documents using PyMuPDF and PyMuPDF4LLM.
"""

import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List

try:
    import pymupdf4llm
except ImportError:
    pymupdf4llm = None

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
    """Parses PDF document handles into structured page records with headers and tables preserved."""

    def parse_document(self, loaded_pdf: LoadedPDF) -> List[ParsedPage]:
        """Extract text, tables, headings, and formatting page-by-page from a loaded PDF."""
        parsed_pages: List[ParsedPage] = []
        file_path_str = str(loaded_pdf.file_path)

        # Method 1: Use PyMuPDF4LLM for high-fidelity Markdown parsing (Headings + Tables)
        if pymupdf4llm is not None:
            try:
                page_chunks = pymupdf4llm.to_markdown(file_path_str, page_chunks=True)
                for chunk in page_chunks:
                    page_num = chunk.get("metadata", {}).get("page", 1)
                    if not isinstance(page_num, int):
                        # Extract 1-indexed page integer if page metadata is offset
                        page_num = len(parsed_pages) + 1

                    parsed_page = ParsedPage(
                        text=chunk.get("text", "").strip(),
                        page_number=page_num,
                        total_pages=loaded_pdf.page_count,
                        source_file=loaded_pdf.filename,
                        file_path=file_path_str,
                        category=loaded_pdf.category,
                    )
                    parsed_pages.append(parsed_page)

                logger.info(
                    f"Parsed {len(parsed_pages)} page(s) with Markdown layout (Tables & Headings) from '{loaded_pdf.filename}'"
                )
                return parsed_pages
            except Exception as e:
                logger.warning(
                    f"pymupdf4llm extraction failed for '{loaded_pdf.filename}' ({e}). Falling back to standard PyMuPDF parser."
                )
                parsed_pages.clear()

        # Method 2: Native PyMuPDF fallback with TableFinder
        doc = loaded_pdf.doc
        for page_idx in range(loaded_pdf.page_count):
            try:
                page = doc.load_page(page_idx)
                
                # Check for tables on page
                tables = page.find_tables()
                if tables.tables:
                    # Replace table regions with markdown table strings
                    raw_text = page.get_text("text")
                    for table in tables.tables:
                        markdown_table = table.to_markdown()
                        # Append markdown table cleanly if not already formatted
                        if markdown_table and "|" not in raw_text:
                            raw_text += f"\n\n{markdown_table}\n\n"
                else:
                    raw_text = page.get_text("text")

                parsed_page = ParsedPage(
                    text=raw_text,
                    page_number=page_idx + 1,
                    total_pages=loaded_pdf.page_count,
                    source_file=loaded_pdf.filename,
                    file_path=file_path_str,
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
        print(sample.text[:500] + "...")

    for pdf in loaded_pdfs:
        pdf.close()
