"""
Document Cleaner Module for NexaCore Knowledge Base RAG (Project 2).

Structure-preserving text cleaner for parsed LlamaIndex Document instances.
Normalizes unicode, removes header/footer boilerplate noise, and tracks character statistics.
"""

import logging
import re
from pathlib import Path
from typing import List, Tuple

from llama_index.core import Document

logger = logging.getLogger(__name__)

# Boilerplate patterns to remove from enterprise docs
BOILERPLATE_PATTERNS = [
    re.compile(r"NexaCore Systems Private Limited\s*\|\s*[A-Z\s]+\|\s*INTERNAL\s*-\s*CONFIDENTIAL", re.IGNORECASE),
    re.compile(r"Page \d+\s*of\s*\d+", re.IGNORECASE),
]

DEFAULT_CLEANED_DIR = Path(__file__).resolve().parent / "cleaned_documents"


class DocumentCleaner:
    """Performs structure-preserving cleaning on LlamaIndex Document objects."""

    def clean_text(self, raw_text: str) -> str:
        """Clean raw text string while preserving markdown headers, bullet points, and tables."""
        if not raw_text:
            return ""

        text = raw_text

        # 1. Normalize unicode spaces & special whitespace
        text = text.replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")

        # 2. Strip boilerplate text patterns
        for pattern in BOILERPLATE_PATTERNS:
            text = pattern.sub("", text)

        # 3. Normalize multiple trailing spaces per line (preserve indentations)
        lines = [line.rstrip() for line in text.split("\n")]

        # 4. Collapse 3 or more consecutive blank lines into at most 2
        cleaned_lines: List[str] = []
        consecutive_blanks = 0

        for line in lines:
            if not line.strip():
                consecutive_blanks += 1
                if consecutive_blanks <= 2:
                    cleaned_lines.append("")
            else:
                consecutive_blanks = 0
                cleaned_lines.append(line)

        cleaned_text = "\n".join(cleaned_lines).strip()
        return cleaned_text

    def clean_document(self, document: Document) -> Document:
        """Clean a single LlamaIndex Document object and update its metadata statistics."""
        raw_text = document.text
        cleaned_text = self.clean_text(raw_text)

        char_before = len(raw_text)
        char_after = len(cleaned_text)
        char_reduction = char_before - char_after
        reduction_pct = (char_reduction / char_before * 100.0) if char_before > 0 else 0.0

        # Update metadata dictionary
        document.metadata["char_count_before"] = char_before
        document.metadata["char_count_after"] = char_after
        document.metadata["char_reduction_percent"] = round(reduction_pct, 2)

        # Update text
        document.set_content(cleaned_text)

        logger.debug(
            f"Cleaned Doc '{document.metadata.get('file_name', 'Doc')}': "
            f"{char_before} -> {char_after} chars ({reduction_pct:.1f}% reduction)"
        )
        return document

    def clean_all_documents(self, documents: List[Document]) -> List[Document]:
        """Clean a list of LlamaIndex Document instances and return updated list."""
        cleaned_docs: List[Document] = []
        total_before = 0
        total_after = 0

        for doc in documents:
            cleaned_doc = self.clean_document(doc)
            cleaned_docs.append(cleaned_doc)
            total_before += cleaned_doc.metadata.get("char_count_before", 0)
            total_after += cleaned_doc.metadata.get("char_count_after", 0)

        total_reduction_pct = ((total_before - total_after) / total_before * 100.0) if total_before > 0 else 0.0

        logger.info(
            f"Cleaning complete for {len(cleaned_docs)} document(s): "
            f"Total raw chars: {total_before:,} -> Cleaned chars: {total_after:,} "
            f"({total_reduction_pct:.1f}% boilerplate removed)"
        )
        return cleaned_docs

    def save_cleaned_documents(self, documents: List[Document], output_dir: str = None) -> Path:
        """Save cleaned document text files to disk categorized by subfolders."""
        target_dir = Path(output_dir if output_dir is not None else DEFAULT_CLEANED_DIR).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)

        saved_count = 0
        for doc in documents:
            category = doc.metadata.get("category", "general")
            file_name = doc.metadata.get("file_name", "document")
            page_num = doc.metadata.get("page_number", 1)
            total_pages = doc.metadata.get("total_pages", 1)

            # Create category subfolder
            cat_dir = target_dir / category
            cat_dir.mkdir(parents=True, exist_ok=True)

            # Construct clean output filename (.md for structure preservation)
            stem = Path(file_name).stem
            out_filename = f"{stem}.md"
            out_path = cat_dir / out_filename

            # Format file content with metadata header comment
            header = (
                f"<!-- METADATA HEADER -->\n"
                f"<!-- File: {file_name} | Category: {category} | Pages: {total_pages} -->\n"
                f"<!-- Chars: {doc.metadata.get('char_count_after', len(doc.text))} -->\n\n"
            )
            out_path.write_text(header + doc.text, encoding="utf-8")
            saved_count += 1

        logger.info(f"Saved {saved_count} cleaned document file(s) to '{target_dir}'")
        return target_dir


if __name__ == "__main__":
    from document_loader import DocumentLoader
    from document_parser import DocumentParser

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    loader = DocumentLoader()
    parser = DocumentParser()
    cleaner = DocumentCleaner()

    discovered = loader.discover_files()
    documents = parser.parse_all_files(discovered)
    cleaned_documents = cleaner.clean_all_documents(documents)

    print("\n" + "=" * 80)
    print(f" CLEANED DOCUMENTS SUMMARY ({len(cleaned_documents)} total)")
    print("=" * 80)
    for doc in cleaned_documents[:5]:
        print(f" - [{doc.metadata.get('file_type').upper()}] {doc.metadata.get('file_name')} | Page {doc.metadata.get('page_number')}/{doc.metadata.get('total_pages')}")
        print(f"   Raw: {doc.metadata.get('char_count_before')} -> Cleaned: {doc.metadata.get('char_count_after')} chars")
        print(f"   Snippet: {doc.text[:120]}...\n")
