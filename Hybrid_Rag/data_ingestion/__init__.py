"""Hybrid RAG Data Ingestion Package (Functional Approach).

Provides incremental data loading, cleaning, parsing, inline validation,
cryptographic hash change detection, and publication routing for Hybrid RAG.
"""

from .document_loader import discover_files, load_all_documents, load_single_document
from .document_parser import parse_document
from .document_cleaner import clean_all_documents, clean_single_document
from .ingestion_state_manager import (
    compute_file_sha256,
    compute_content_sha256,
    load_ingestion_state,
    save_ingestion_state,
    detect_catalog_changes,
)
from .inline_document_validator import evaluate_document_for_ingestion
from .incremental_data_pipeline import run_incremental_datapipeline

__all__ = [
    "discover_files",
    "load_all_documents",
    "load_single_document",
    "parse_document",
    "clean_all_documents",
    "clean_single_document",
    "compute_file_sha256",
    "compute_content_sha256",
    "load_ingestion_state",
    "save_ingestion_state",
    "detect_catalog_changes",
    "evaluate_document_for_ingestion",
    "run_incremental_datapipeline",
]
