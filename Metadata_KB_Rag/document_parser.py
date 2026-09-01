"""
Document Parser & Metadata Enricher Module for NexaCore Knowledge Base RAG (Project 2).

Enriches LlamaIndex Document objects loaded via SimpleDirectoryReader with
document_type classification, UUIDs, and section tracking.
"""

import logging
import uuid
from pathlib import Path
from typing import List

from llama_index.core import Document

logger = logging.getLogger(__name__)


class DocumentParser:
    """Enriches and normalizes LlamaIndex Document instances with domain metadata."""

    @staticmethod
    def infer_document_type(file_name: str) -> str:
        """Dynamically infer document_type classification based on filename patterns."""
        fn = file_name.lower()
        if "handbook" in fn:
            return "employee_handbook"
        elif "policy" in fn or "leave" in fn or "remote" in fn:
            return "policy_document"
        elif "api" in fn or "standard" in fn or "schema" in fn or "architecture" in fn:
            return "technical_standard"
        elif "guide" in fn or "sop" in fn or "manual" in fn or "workflow" in fn:
            return "operating_guide"
        elif "finance" in fn or "reimbursement" in fn or "budget" in fn or "payroll" in fn:
            return "financial_document"
        elif "security" in fn or "compliance" in fn or "audit" in fn or "incident" in fn:
            return "security_compliance"
        else:
            return "general_document"

    def enrich_document(self, document: Document) -> Document:
        """Enrich a single LlamaIndex Document instance with metadata annotations."""
        file_name = document.metadata.get("file_name", Path(document.metadata.get("file_path", "doc")).name)
        
        document.metadata["document_type"] = self.infer_document_type(file_name)
        if "doc_id" not in document.metadata:
            document.metadata["doc_id"] = str(uuid.uuid5(uuid.NAMESPACE_DNS, file_name))
        
        # Standardize page numbers if missing
        if "page_number" not in document.metadata:
            document.metadata["page_number"] = document.metadata.get("page_label", 1)
        if "total_pages" not in document.metadata:
            document.metadata["total_pages"] = 1

        logger.debug(f"Enriched LlamaIndex Document '{file_name}' -> type: '{document.metadata['document_type']}'")
        return document

    def enrich_all_documents(self, documents: List[Document]) -> List[Document]:
        """Enrich a list of LlamaIndex Document instances."""
        enriched = [self.enrich_document(doc) for doc in documents]
        logger.info(f"Enriched {len(enriched)} LlamaIndex Document object(s) with domain metadata.")
        return enriched


if __name__ == "__main__":
    from document_loader import DocumentLoader

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    loader = DocumentLoader()
    parser = DocumentParser()

    raw_docs = loader.load_documents()
    enriched_docs = parser.enrich_all_documents(raw_docs)

    print("\n" + "=" * 80)
    print(f" ENRICHED LLAMAINDEX DOCUMENTS ({len(enriched_docs)} total)")
    print("=" * 80)
    for doc in enriched_docs[:5]:
        print(f" - [ID: {doc.doc_id[:12]}...] {doc.metadata.get('source')} | Type: {doc.metadata.get('document_type')}")
        print(f"   Snippet: {doc.text[:120]}...\n")
