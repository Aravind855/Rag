"""
Recursive Document Chunking Module for NexaCore Semantic Document Search.

Splits cleaned PDF document text recursively using hierarchical separators
(\\n\\n -> \\n -> sentence boundaries -> spaces -> characters) to preserve semantic cohesion,
while retaining document metadata across every chunk.
"""

import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from document_cleaner import CleanedPage

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    RecursiveCharacterTextSplitter = None

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """Structured representation of a document text chunk with RAG metadata."""
    chunk_id: str
    text: str
    chunk_index: int
    char_count: int
    token_count: int
    page_number: int
    total_pages: int
    source_file: str
    file_path: str
    category: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk metadata into a plain dictionary."""
        return asdict(self)


class CustomRecursiveTextSplitter:
    """Pure Python Recursive Character Text Splitter fallback.

    Splits text hierarchically using specified separators:
    Paragraphs (\\n\\n) -> Lines (\\n) -> Sentences (. , ! , ? ) -> Spaces ( ) -> Characters ("").
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", "! ", "? ", "; ", " ", ""]

    def split_text(self, text: str) -> List[str]:
        """Recursively split text into chunks respecting chunk_size and chunk_overlap."""
        if not text:
            return []

        return self._split_recursive(text, self.separators, self.chunk_size, self.chunk_overlap)

    def _split_recursive(self, text: str, separators: List[str], max_size: int, overlap: int) -> List[str]:
        if len(text) <= max_size:
            return [text] if text.strip() else []

        # Find best separator that splits text into smaller components
        chosen_separator = ""
        for sep in separators:
            if sep == "":
                chosen_separator = ""
                break
            if sep in text:
                chosen_separator = sep
                break

        if chosen_separator != "":
            splits = text.split(chosen_separator)
        else:
            splits = list(text)

        # Merge splits into chunks under max_size with overlap
        chunks: List[str] = []
        current_chunk: List[str] = []
        current_len = 0

        for split in splits:
            item = split + chosen_separator if chosen_separator else split
            item_len = len(item)

            # If a single item exceeds max_size and we have remaining separators, split it recursively
            if item_len > max_size and len(separators) > 1:
                next_seps = separators[separators.index(chosen_separator) + 1 :] if chosen_separator in separators else separators[1:]
                sub_chunks = self._split_recursive(split, next_seps, max_size, overlap)
                for sub in sub_chunks:
                    if current_len + len(sub) > max_size and current_chunk:
                        chunk_str = "".join(current_chunk).strip()
                        if chunk_str:
                            chunks.append(chunk_str)
                        # Retain overlap from end of current_chunk
                        current_chunk = self._get_overlap_items(current_chunk, overlap)
                        current_len = sum(len(x) for x in current_chunk)

                    current_chunk.append(sub + " ")
                    current_len += len(sub) + 1
                continue

            if current_len + item_len > max_size and current_chunk:
                chunk_str = "".join(current_chunk).strip()
                if chunk_str:
                    chunks.append(chunk_str)
                current_chunk = self._get_overlap_items(current_chunk, overlap)
                current_len = sum(len(x) for x in current_chunk)

            current_chunk.append(item)
            current_len += item_len

        if current_chunk:
            final_str = "".join(current_chunk).strip()
            if final_str:
                chunks.append(final_str)

        return chunks

    def _get_overlap_items(self, items: List[str], overlap_size: int) -> List[str]:
        """Extract tail items up to overlap_size characters."""
        overlap_items: List[str] = []
        curr_size = 0
        for item in reversed(items):
            if curr_size + len(item) <= overlap_size:
                overlap_items.insert(0, item)
                curr_size += len(item)
            else:
                break
        return overlap_items


class RecursiveDocumentChunker:
    """Recursive Document Chunker with metadata preservation."""

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        separators: Optional[List[str]] = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", "! ", "? ", "; ", " ", ""]

        if RecursiveCharacterTextSplitter is not None:
            self.splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=self.separators,
                is_separator_regex=False,
            )
            logger.info("Initialized LangChain RecursiveCharacterTextSplitter.")
        else:
            self.splitter = CustomRecursiveTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=self.separators,
            )
            logger.info("Initialized CustomRecursiveTextSplitter fallback.")

    def chunk_page(self, page: CleanedPage, doc_chunk_offset: int = 0) -> List[DocumentChunk]:
        """Split a single CleanedPage into metadata-enriched DocumentChunk objects."""
        raw_chunks = self.splitter.split_text(page.text)
        doc_chunks: List[DocumentChunk] = []

        # Create clean prefix stem for chunk_id
        file_stem = re.sub(r"[^a-zA-Z0-9_]", "_", Path(page.source_file).stem)

        for i, text_chunk in enumerate(raw_chunks):
            chunk_idx = doc_chunk_offset + i
            chunk_id = f"{file_stem}_p{page.page_number}_c{i}"
            char_count = len(text_chunk)
            token_estimate = max(1, char_count // 4)

            chunk_obj = DocumentChunk(
                chunk_id=chunk_id,
                text=text_chunk,
                chunk_index=chunk_idx,
                char_count=char_count,
                token_count=token_estimate,
                page_number=page.page_number,
                total_pages=page.total_pages,
                source_file=page.source_file,
                file_path=page.file_path,
                category=page.category,
            )
            doc_chunks.append(chunk_obj)

        return doc_chunks

    def chunk_all_pages(self, cleaned_pages: List[CleanedPage]) -> List[DocumentChunk]:
        """Chunk all CleanedPage objects across all documents."""
        all_chunks: List[DocumentChunk] = []
        doc_chunk_counters: Dict[str, int] = {}

        for page in cleaned_pages:
            offset = doc_chunk_counters.get(page.source_file, 0)
            page_chunks = self.chunk_page(page, doc_chunk_offset=offset)
            all_chunks.extend(page_chunks)
            doc_chunk_counters[page.source_file] = offset + len(page_chunks)

        logger.info(
            f"Generated {len(all_chunks)} chunks from {len(cleaned_pages)} pages "
            f"(Target Chunk Size: {self.chunk_size}, Overlap: {self.chunk_overlap})"
        )
        return all_chunks


if __name__ == "__main__":
    from pathlib import Path
    from document_cleaner import PDFDocumentCleaner
    from document_loader import PDFDocumentLoader
    from document_parser import PDFDocumentParser

    logging.basicConfig(level=logging.INFO)
    loader = PDFDocumentLoader()
    parser = PDFDocumentParser()
    cleaner = PDFDocumentCleaner()
    chunker = RecursiveDocumentChunker(chunk_size=600, chunk_overlap=100)

    loaded_pdfs = loader.load_all_pdfs()
    parsed_pages = parser.parse_all_documents(loaded_pdfs)
    cleaned_pages = cleaner.clean_all_pages(parsed_pages)
    chunks = chunker.chunk_all_pages(cleaned_pages)

    print(f"\nGenerated total {len(chunks)} text chunks.")
    if chunks:
        sample = chunks[0]
        print(f"\n--- Sample Chunk (ID: {sample.chunk_id}, Category: {sample.category}, Source: {sample.source_file}, Page {sample.page_number}) ---")
        print(f"Char Count: {sample.char_count} | Token Estimate: {sample.token_count}")
        print("\nChunk Text:\n")
        print(sample.text)

    for pdf in loaded_pdfs:
        pdf.close()
