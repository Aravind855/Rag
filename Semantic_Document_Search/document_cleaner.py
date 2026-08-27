"""
Document Cleaning & Normalization Module for NexaCore Semantic Document Search.

Cleans raw extracted PDF text while strictly preserving document structure,
headings, numbered lists (e.g. 1.1 Casual Leave), bullet points, and paragraph boundaries.
"""

import logging
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List

from document_parser import ParsedPage

logger = logging.getLogger(__name__)


@dataclass
class CleanedPage:
    """Structured representation of a cleaned and normalized PDF page."""
    text: str
    raw_text: str
    page_number: int
    total_pages: int
    source_file: str
    file_path: str
    category: str
    char_count_before: int
    char_count_after: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert cleaned page metadata into a plain dictionary."""
        return asdict(self)


class PDFDocumentCleaner:
    """Structure-preserving text cleaner for PDF document pages."""

    def __init__(self, fix_hyphenation: bool = True, normalize_spaces: bool = True):
        self.fix_hyphenation = fix_hyphenation
        self.normalize_spaces = normalize_spaces

    def clean_text(self, text: str) -> str:
        """Clean raw text string while strictly preserving section structure & formatting.

        Steps:
        1. Strip non-printable control characters.
        2. Fix hyphenated word breaks at end of lines (e.g., 'sub-\nstantive' -> 'substantive').
        3. Replace Windows carriage returns (\r\n -> \n).
        4. Normalize repeated blank lines (3+ newlines -> 2 newlines).
        5. Normalize inline spaces (multiple spaces/tabs to single space) per line while preserving newline breaks.
        6. Retain all section headings (e.g., '1. Leave Policy', '1.1 Casual Leave'), bullets, punctuation, & case.
        """
        if not text:
            return ""

        # 1. Remove non-printable control characters (except \n and \t)
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

        # 2. Fix hyphenation split across line breaks (e.g. "word-\nnext" -> "wordnext")
        if self.fix_hyphenation:
            cleaned = re.sub(r"(\b[a-zA-Z]+)-\n([a-zA-Z]+\b)", r"\1\2", cleaned)

        # 3. Standardize line endings to Unix style (\n)
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

        # 4. Process line-by-line to preserve structure and normalize inline whitespace
        lines = cleaned.split("\n")
        cleaned_lines = []
        for line in lines:
            # Collapse multiple spaces or tabs into a single space per line
            if self.normalize_spaces:
                line = re.sub(r"[ \t]+", " ", line)
            cleaned_lines.append(line.strip())

        # Rejoin lines
        cleaned = "\n".join(cleaned_lines)

        # 5. Normalize excessive blank lines (more than 2 consecutive newlines -> 2 newlines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        return cleaned.strip()

    def clean_page(self, page: ParsedPage) -> CleanedPage:
        """Clean text of a single ParsedPage object."""
        raw_text = page.text
        cleaned_text = self.clean_text(raw_text)

        cleaned_page = CleanedPage(
            text=cleaned_text,
            raw_text=raw_text,
            page_number=page.page_number,
            total_pages=page.total_pages,
            source_file=page.source_file,
            file_path=page.file_path,
            category=page.category,
            char_count_before=len(raw_text),
            char_count_after=len(cleaned_text),
        )
        return cleaned_page

    def clean_all_pages(self, parsed_pages: List[ParsedPage]) -> List[CleanedPage]:
        """Clean all ParsedPage objects in a list."""
        cleaned_pages: List[CleanedPage] = []
        for page in parsed_pages:
            cleaned = self.clean_page(page)
            cleaned_pages.append(cleaned)

        total_before = sum(p.char_count_before for p in cleaned_pages)
        total_after = sum(p.char_count_after for p in cleaned_pages)
        logger.info(
            f"Cleaned {len(cleaned_pages)} pages. Total chars: {total_before} -> {total_after} "
            f"({total_before - total_after} chars normalized)"
        )
        return cleaned_pages


if __name__ == "__main__":
    from document_loader import PDFDocumentLoader
    from document_parser import PDFDocumentParser

    logging.basicConfig(level=logging.INFO)
    loader = PDFDocumentLoader()
    parser = PDFDocumentParser()
    cleaner = PDFDocumentCleaner()

    loaded_pdfs = loader.load_all_pdfs()
    parsed_pages = parser.parse_all_documents(loaded_pdfs)
    cleaned_pages = cleaner.clean_all_pages(parsed_pages)

    if cleaned_pages:
        sample = cleaned_pages[0]
        print(f"\n--- Cleaned Page Sample ({sample.source_file}, Page {sample.page_number}) ---")
        print(f"Chars before: {sample.char_count_before} | Chars after: {sample.char_count_after}")
        print("\nCleaned Text Snippet:\n")
        print(sample.text[:400])

    for pdf in loaded_pdfs:
        pdf.close()
