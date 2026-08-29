"""
Document Parser Module for NexaCore Knowledge Base RAG (Project 2).

Parses discovered files (.pdf, .docx, .md, .txt) into LlamaIndex Document objects,
preserving page numbers, section headings, and rich file-level metadata payload.
"""

import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import pymupdf as fitz  # PyMuPDF
import pymupdf4llm  # Structure-aware PDF to Markdown parser
import docx  # python-docx
from llama_index.core import Document

from document_loader import DiscoveredFile, DocumentLoader

logger = logging.getLogger(__name__)


class DocumentParser:
    """Multi-format parser generating LlamaIndex Document instances with rich metadata."""

    def parse_file(self, discovered_file: DiscoveredFile) -> List[Document]:
        """Parse a DiscoveredFile instance into one or more LlamaIndex Document objects."""
        file_path = discovered_file.file_path
        file_type = discovered_file.file_type.lower()

        logger.info(f"Parsing [{file_type.upper()}] '{discovered_file.file_name}'...")

        if file_type == "pdf":
            return self._parse_pdf(discovered_file)
        elif file_type == "docx":
            return self._parse_docx(discovered_file)
        elif file_type == "md":
            return self._parse_markdown(discovered_file)
        elif file_type == "txt":
            return self._parse_txt(discovered_file)
        else:
            logger.warning(f"Unsupported file type '{file_type}' for '{file_path.name}'. Skipping.")
            return []

    def _parse_pdf(self, file_info: DiscoveredFile) -> List[Document]:
        """Parse PDF into structure-aware Markdown using pymupdf4llm, preserving tables and headers."""
        try:
            # Extract PDF as structured Markdown (preserves tables, headers, lists)
            md_text = pymupdf4llm.to_markdown(str(file_info.file_path))
            if not md_text or not md_text.strip():
                logger.warning(f"PDF '{file_info.file_name}' contains no readable text.")
                return []
                

            with fitz.open(file_info.file_path) as doc:
                total_pages = doc.page_count

            metadata = file_info.to_metadata_dict()
            metadata["page_number"] = 1
            metadata["total_pages"] = total_pages
            metadata["doc_id"] = str(uuid.uuid5(uuid.NAMESPACE_DNS, file_info.file_name))

            llama_doc = Document(
                text=md_text.strip(),
                metadata=metadata,
                doc_id=metadata["doc_id"],
            )
            logger.info(
                f"Parsed PDF '{file_info.file_name}' via PyMuPDF4LLM: "
                f"Extracted {len(md_text)} characters across {total_pages} page(s)."
            )
            return [llama_doc]

        except Exception as e:
            logger.error(f"Failed to parse PDF '{file_info.file_name}': {e}")
            return []

    def _parse_docx(self, file_info: DiscoveredFile) -> List[Document]:
        """Parse DOCX document using python-docx, preserving paragraph text and table content."""
        try:
            doc = docx.Document(file_info.file_path)
            paragraphs_text = []

            for p in doc.paragraphs:
                text = p.text.strip()
                if text:
                    paragraphs_text.append(text)

            # Also extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        paragraphs_text.append(f"[Table Row] {row_text}")

            full_text = "\n\n".join(paragraphs_text)
            if not full_text:
                logger.warning(f"DOCX '{file_info.file_name}' contains no readable text.")
                return []

            metadata = file_info.to_metadata_dict()
            metadata["page_number"] = 1
            metadata["total_pages"] = 1
            metadata["doc_id"] = str(uuid.uuid5(uuid.NAMESPACE_DNS, file_info.file_name))

            llama_doc = Document(
                text=full_text,
                extra_info=metadata,
                doc_id=metadata["doc_id"],
            )
            logger.info(f"Parsed DOCX '{file_info.file_name}': Extracted {len(full_text)} characters.")
            return [llama_doc]

        except Exception as e:
            logger.error(f"Failed to parse DOCX '{file_info.file_name}': {e}")
            return []

    def _parse_markdown(self, file_info: DiscoveredFile) -> List[Document]:
        """Parse Markdown file using UTF-8 text reader."""
        try:
            text = file_info.file_path.read_text(encoding="utf-8").strip()
            if not text:
                logger.warning(f"Markdown file '{file_info.file_name}' is empty.")
                return []

            metadata = file_info.to_metadata_dict()
            metadata["page_number"] = 1
            metadata["total_pages"] = 1
            metadata["doc_id"] = str(uuid.uuid5(uuid.NAMESPACE_DNS, file_info.file_name))

            llama_doc = Document(
                text=text,
                extra_info=metadata,
                doc_id=metadata["doc_id"],
            )
            logger.info(f"Parsed Markdown '{file_info.file_name}': Extracted {len(text)} characters.")
            return [llama_doc]

        except Exception as e:
            logger.error(f"Failed to parse Markdown '{file_info.file_name}': {e}")
            return []

    def _parse_txt(self, file_info: DiscoveredFile) -> List[Document]:
        """Parse plain Text file using UTF-8 text reader."""
        try:
            text = file_info.file_path.read_text(encoding="utf-8").strip()
            if not text:
                logger.warning(f"TXT file '{file_info.file_name}' is empty.")
                return []

            metadata = file_info.to_metadata_dict()
            metadata["page_number"] = 1
            metadata["total_pages"] = 1
            metadata["doc_id"] = str(uuid.uuid5(uuid.NAMESPACE_DNS, file_info.file_name))

            llama_doc = Document(
                text=text,
                extra_info=metadata,
                doc_id=metadata["doc_id"],
            )
            logger.info(f"Parsed TXT '{file_info.file_name}': Extracted {len(text)} characters.")
            return [llama_doc]

        except Exception as e:
            logger.error(f"Failed to parse TXT '{file_info.file_name}': {e}")
            return []

    def parse_all_files(self, discovered_files: List[DiscoveredFile]) -> List[Document]:
        """Parse a list of DiscoveredFile records into LlamaIndex Document instances."""
        all_documents: List[Document] = []
        for file_info in discovered_files:
            docs = self.parse_file(file_info)
            all_documents.extend(docs)

        logger.info(f"Parsing complete: Generated {len(all_documents)} LlamaIndex Document object(s).")
        return all_documents


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    loader = DocumentLoader()
    parser = DocumentParser()

    discovered = loader.discover_files()
    documents = parser.parse_all_files(discovered)

    print("\n" + "=" * 80)
    print(f" PARSED DOCUMENTS SUMMARY ({len(documents)} total LlamaIndex Document objects)")
    print("=" * 80)
    for doc in documents[:5]:  # Print preview of first 5 documents
        print(f" - [ID: {doc.doc_id[:12]}...] {doc.extra_info.get('file_name')} | Page: {doc.extra_info.get('page_number')}/{doc.extra_info.get('total_pages')} | Category: {doc.extra_info.get('category')}")
        print(f"   Snippet: {doc.text[:120]}...\n")
