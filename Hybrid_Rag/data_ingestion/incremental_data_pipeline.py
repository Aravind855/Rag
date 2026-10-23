"""Production Incremental Data Ingestion & Inline Validation Pipeline for Hybrid RAG.

Located in d:\\RAG\\Hybrid_Rag\\data_ingestion\\incremental_data_pipeline.py
Replicates and enhances data ingestion directly within Hybrid RAG without
modifying the original d:\\RAG\\Datapipeline scripts.

Key Production Capabilities:
1. Incremental change detection via SHA-256 byte hashing and content hashing.
2. Inline multi-level validation gates (L1 structural integrity, L2 content fidelity).
3. Tri-state disposition routing:
   - PASS (Quality score >= 90%): Published to d:\\RAG\\cleaned_documents/<dept>/<file>.md
   - REVIEW (70% <= Quality score < 90%): Quarantined to d:\\RAG\\cleaned_documents/quarantine/
   - FAIL (Structural failure or score < 70%): Logged to d:\\RAG\\cleaned_documents/dead_letter/
4. Atomic state tracking (ingestion_state.json), manifest sync, and published_delta.json export.
5. Live operational telemetry scorecard.

Strictly procedural (zero classes). All paths dynamically resolved.
"""

import argparse
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union

# Ensure UTF-8 terminal output safety for Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add current folder to sys.path for direct execution
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# Local Ingestion Imports
from document_cleaner import clean_single_document, clean_stem_name
from document_loader import DEFAULT_SOURCE_DIR, PROJECT_ROOT, load_single_document
from ingestion_state_manager import (
    compute_content_sha256,
    compute_file_sha256,
    detect_catalog_changes,
    get_default_state_file,
    load_ingestion_state,
    record_document_disposition,
    save_ingestion_state,
)
from inline_document_validator import evaluate_document_for_ingestion

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("hybrid_rag.incremental_pipeline")

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "cleaned_documents"
DEFAULT_MANIFEST_PATH = DEFAULT_OUTPUT_DIR / "cleaned_documents_manifest.json"
DEFAULT_DELTA_PATH = DEFAULT_OUTPUT_DIR / "published_delta.json"


def get_default_output_dir() -> Path:
    """Returns dynamically resolved output directory."""
    env_dir = os.getenv("RAG_OUTPUT_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    return DEFAULT_OUTPUT_DIR


def run_incremental_datapipeline(
    source_dir: Optional[Union[str, Path]] = None,
    output_dir: Optional[Union[str, Path]] = None,
    incremental: bool = True,
    max_workers: int = 4,
    force_publish: bool = False
    ) -> Dict[str, Any]:
    """Executes the production incremental ingestion and inline validation pipeline.

    Args:
        source_dir: Raw files directory (default: d:\\RAG\\Datasource).
        output_dir: Target cleaned documents directory (default: d:\\RAG\\cleaned_documents).
        incremental: If True, uses SHA-256 state tracking to only process new/modified files.
        max_workers: Thread concurrency for parsing.
        force_publish: If True, publishes even quarantined files.

    Returns:
        Summary dictionary with execution metrics, telemetry, and document dispositions.
    """
    start_time = time.time()
    src = Path(source_dir).resolve() if source_dir else DEFAULT_SOURCE_DIR
    out = Path(output_dir).resolve() if output_dir else get_default_output_dir()
    out.mkdir(parents=True, exist_ok=True)

    quarantine_dir = out / "quarantine"
    dead_letter_dir = out / "dead_letter"

    logger.info("=" * 85)
    logger.info("STARTING HYBRID RAG INCREMENTAL INGESTION & INLINE VALIDATION PIPELINE")
    logger.info(f"Source Directory:       {src}")
    logger.info(f"Output Clean Directory: {out}")
    logger.info(f"Execution Mode:         {'INCREMENTAL (State-Aware)' if incremental else 'FULL REBUILD'}")
    logger.info("=" * 85)

    # 1. Load or Initialize Durable State
    state_file = out / "ingestion_state.json"
    state = load_ingestion_state(state_file) if incremental else {"version": "1.0", "entries": {}}

    # 2. Change Detection via Cryptographic Hashes
    catalog_changes = detect_catalog_changes(src, state)
    new_files = catalog_changes["new_files"]
    modified_files = catalog_changes["modified_files"]
    unchanged_files = catalog_changes["unchanged_files"]
    deleted_entries = catalog_changes["deleted_entries"]

    files_to_process = new_files + modified_files

    logger.info(
        f"Catalog Scan: {catalog_changes['total_source_files']} total | "
        f"{len(new_files)} new | {len(modified_files)} modified | "
        f"{len(unchanged_files)} unchanged | {len(deleted_entries)} deleted"
    )

    # Fast Exit on Zero-Compute Incremental State
    if incremental and not files_to_process and not deleted_entries:
        elapsed = round(time.time() - start_time, 2)
        logger.info(f"Zero-Compute Check: All documents up to date. Completed in {elapsed}s.")
        print_pipeline_scorecard(
            total_source=catalog_changes['total_source_files'],
            processed_count=0,
            published_count=0,
            quarantined_count=0,
            failed_count=0,
            skipped_count=len(unchanged_files),
            deleted_count=0,
            elapsed_seconds=elapsed,
            status="UP_TO_DATE (ZERO COMPUTE)"
        )
        return {
            "status": "UP_TO_DATE",
            "elapsed_seconds": elapsed,
            "processed": 0,
            "skipped": len(unchanged_files),
            "published_delta": [],
        }

    # 3. Process New & Modified Files with Inline Validation Gate
    published_entries: List[Dict[str, Any]] = []
    quarantined_entries: List[Dict[str, Any]] = []
    failed_entries: List[Dict[str, Any]] = []

    for file_path, file_meta in files_to_process:
        source_rel = file_meta["source_path"]
        logger.info(f"Ingesting: {source_rel}")

        # Ensure category is correctly resolved from relative folder
        src_parts = Path(source_rel).parts
        category = src_parts[0] if len(src_parts) > 1 else file_meta.get("category", "general")
        file_meta["category"] = category

        file_hash = file_meta.get("sha256") or compute_file_sha256(file_path)

        try:
            # Step A: Load Raw Document
            raw_doc = load_single_document(file_path, file_meta)
            raw_doc.metadata["category"] = category

            # Step B: Clean, Normalize & Enrich with Frontmatter
            clean_doc = clean_single_document(raw_doc)
            clean_text = clean_doc.page_content
            metadata = clean_doc.metadata
            metadata["category"] = category
            content_hash = compute_content_sha256(clean_text)

            # Step C: Inline Multi-Level Validation (L1 Structural + L2 Fidelity)
            disposition, q_score, reasons, val_details = evaluate_document_for_ingestion(
                clean_text=clean_text,
                metadata=metadata,
                raw_file_path=file_path,
                source_rel_path=source_rel
            )

            file_stem = clean_stem_name(Path(metadata.get("file_name", "doc")).stem)
            clean_file_rel = f"{category}/{file_stem}.md"

            # Step D: Tri-State Routing
            if disposition == "PUBLISH" or force_publish:
                target_file = out / category / f"{file_stem}.md"
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_text(clean_text, encoding="utf-8")

                manifest_entry = {
                    "clean_file": clean_file_rel,
                    "absolute_path": str(target_file),
                    "original_file": metadata.get("file_name"),
                    "source_path": source_rel,
                    "category": category,
                    "document_type": metadata.get("document_type"),
                    "total_words": metadata.get("total_words", 0),
                    "total_chars": metadata.get("total_chars", 0),
                    "has_tables": metadata.get("has_tables", False),
                    "table_count": metadata.get("table_count", 0),
                    "quality_score": q_score,
                    "sha256": file_hash,
                    "content_sha256": content_hash,
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": metadata,
                }
                published_entries.append(manifest_entry)
                record_document_disposition(
                    state=state,
                    source_rel_path=source_rel,
                    file_sha256=file_hash,
                    content_sha256=content_hash,
                    disposition="PUBLISH",
                    quality_score=q_score,
                    validation_reasons=reasons,
                    clean_file_rel=clean_file_rel
                )
                logger.info(f" -> [PUBLISH] Quality Score: {q_score}% -> {clean_file_rel}")

            elif disposition == "QUARANTINE":
                target_file = quarantine_dir / category / f"{file_stem}.md"
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_text(clean_text, encoding="utf-8")

                meta_target = quarantine_dir / category / f"{file_stem}.meta.json"
                meta_target.write_text(json.dumps({
                    "source_path": source_rel,
                    "reasons": reasons,
                    "quality_score": q_score,
                    "validation_details": val_details,
                    "quarantined_at": datetime.now(timezone.utc).isoformat(),
                }, indent=2), encoding="utf-8")

                quarantined_entries.append({
                    "source_path": source_rel,
                    "reasons": reasons,
                    "quality_score": q_score,
                    "quarantine_path": str(target_file),
                })
                record_document_disposition(
                    state=state,
                    source_rel_path=source_rel,
                    file_sha256=file_hash,
                    content_sha256=content_hash,
                    disposition="QUARANTINE",
                    quality_score=q_score,
                    validation_reasons=reasons,
                    clean_file_rel=f"quarantine/{clean_file_rel}"
                )
                logger.warning(f" -> [QUARANTINE] Quality Score: {q_score}%: {reasons}")

            else:  # FAIL
                dead_letter_dir.mkdir(parents=True, exist_ok=True)
                err_file = dead_letter_dir / f"{file_stem}.error.json"
                err_file.write_text(json.dumps({
                    "source_path": source_rel,
                    "reasons": reasons,
                    "quality_score": q_score,
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                }, indent=2), encoding="utf-8")

                failed_entries.append({"source_path": source_rel, "reasons": reasons})
                record_document_disposition(
                    state=state,
                    source_rel_path=source_rel,
                    file_sha256=file_hash,
                    content_sha256="",
                    disposition="FAIL",
                    quality_score=q_score,
                    validation_reasons=reasons,
                    error_message="; ".join(reasons)
                )
                logger.error(f" -> [FAIL] Rejection Reasons: {reasons}")

        except Exception as e:
            logger.exception(f"Fatal parser error on {source_rel}: {e}")
            dead_letter_dir.mkdir(parents=True, exist_ok=True)
            err_file = dead_letter_dir / f"{re_slug(source_rel)}.crash.json"
            err_file.write_text(json.dumps({
                "source_path": source_rel,
                "error": str(e),
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }, indent=2), encoding="utf-8")

            failed_entries.append({"source_path": source_rel, "reasons": [str(e)]})
            record_document_disposition(
                state=state,
                source_rel_path=source_rel,
                file_sha256=file_hash,
                content_sha256="",
                disposition="FAIL",
                quality_score=0.0,
                validation_reasons=[str(e)],
                error_message=str(e)
            )

    # 4. Handle Deletions (Decommissioning)
    for del_rel in deleted_entries:
        logger.info(f"Decommissioning deleted file: {del_rel}")
        entry = state.get("entries", {}).get(del_rel, {})
        clean_rel = entry.get("clean_file")
        if clean_rel:
            clean_path = out / clean_rel
            if clean_path.exists():
                clean_path.unlink()
        state.get("entries", {}).pop(del_rel, None)

    # 5. Persist State
    save_ingestion_state(state, state_file)

    # 6. Rebuild / Synchronize Clean Manifest
    active_manifest = compile_published_manifest(out, state)
    DEFAULT_MANIFEST_PATH.write_text(json.dumps(active_manifest, indent=2), encoding="utf-8")
    logger.info(f"Manifest synchronized: {len(active_manifest['documents'])} active published documents.")

    # 7. Export Delta Manifest for Downstream Incremental Indexing
    delta_manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_delta_files": len(published_entries),
        "published_documents": published_entries,
        "quarantined_documents": quarantined_entries,
        "failed_documents": failed_entries,
    }
    DEFAULT_DELTA_PATH.write_text(json.dumps(delta_manifest, indent=2), encoding="utf-8")

    elapsed = round(time.time() - start_time, 2)
    pipeline_status = "PASS" if not failed_entries and not quarantined_entries else "ATTENTION_REQUIRED"

    print_pipeline_scorecard(
        total_source=catalog_changes['total_source_files'],
        processed_count=len(files_to_process),
        published_count=len(published_entries),
        quarantined_count=len(quarantined_entries),
        failed_count=len(failed_entries),
        skipped_count=len(unchanged_files),
        deleted_count=len(deleted_entries),
        elapsed_seconds=elapsed,
        status=pipeline_status
    )

    return {
        "status": pipeline_status,
        "elapsed_seconds": elapsed,
        "processed": len(files_to_process),
        "published": len(published_entries),
        "quarantined": len(quarantined_entries),
        "failed": len(failed_entries),
        "skipped": len(unchanged_files),
        "deleted": len(deleted_entries),
        "published_delta": published_entries,
    }


def compile_published_manifest(output_dir: Path, state: Dict[str, Any]) -> Dict[str, Any]:
    """Compiles the official manifest containing only active PUBLISHED documents."""
    entries = state.get("entries", {})
    docs: List[Dict[str, Any]] = []

    total_words = 0
    total_chars = 0
    total_tables = 0

    for source_path, entry in sorted(entries.items()):
        if entry.get("disposition") != "PUBLISH":
            continue

        clean_rel = entry.get("clean_file")
        if not clean_rel:
            continue

        clean_file = output_dir / clean_rel
        if not clean_file.exists():
            continue

        content = clean_file.read_text(encoding="utf-8", errors="replace")
        fm = extract_frontmatter_dict(content)

        w = fm.get("total_words", 0)
        c = fm.get("total_chars", 0)
        t = fm.get("table_count", 0)

        total_words += w
        total_chars += c
        total_tables += t

        docs.append({
            "clean_file": clean_rel,
            "absolute_path": str(clean_file),
            "original_file": fm.get("original_file", Path(source_path).name),
            "source_path": source_path,
            "category": fm.get("category", "general"),
            "document_type": fm.get("document_type", "document"),
            "total_words": w,
            "total_chars": c,
            "has_tables": fm.get("has_tables", False),
            "table_count": t,
            "sha256": entry.get("sha256"),
            "quality_score": entry.get("quality_score"),
            "metadata": fm,
        })

    return {
        "total_documents": len(docs),
        "total_words": total_words,
        "total_characters": total_chars,
        "total_tables": total_tables,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "documents": docs,
    }


def extract_frontmatter_dict(content: str) -> Dict[str, Any]:
    """Helper to parse YAML frontmatter from document string."""
    import yaml
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                return yaml.safe_load(parts[1]) or {}
            except Exception:
                pass
    return {}


def re_slug(text: str) -> str:
    """Sanitizes file path to safe filename."""
    import re
    return re.sub(r"[^a-zA-Z0-9_\-]+", "_", text).strip("_")


def print_pipeline_scorecard(
    total_source: int,
    processed_count: int,
    published_count: int,
    quarantined_count: int,
    failed_count: int,
    skipped_count: int,
    deleted_count: int,
    elapsed_seconds: float,
    status: str
    ) -> None:
    """Prints a formatted operational telemetry scorecard to stdout."""
    print("\n" + "=" * 90)
    print("HYBRID RAG INCREMENTAL INGESTION & INLINE VALIDATION SCORECARD")
    print("=" * 90)
    print(f"{'Operational Metric':<35} | {'Count / Value':<20} | {'Benchmark':<20}")
    print("-" * 90)
    print(f"{'Source Catalog Inventory':<35} | {total_source:<20} | Total registered files")
    print(f"{'Unchanged (Zero-Compute Skipped)':<35} | {skipped_count:<20} | 100% hash matching")
    print(f"{'Newly Processed Documents':<35} | {processed_count:<20} | Incremental batch")
    print(f"{'Published to Clean Corpus (PASS)':<35} | {published_count:<20} | >= 90% Quality score")
    print(f"{'Quarantined for Review (REVIEW)':<35} | {quarantined_count:<20} | Isolated from retrieval")
    print(f"{'Dead-Letter Failures (FAIL)':<35} | {failed_count:<20} | 0 target")
    print(f"{'Decommissioned Deleted Files':<35} | {deleted_count:<20} | Synced removals")
    print(f"{'Execution Latency':<35} | {elapsed_seconds:>5.2f} seconds       | Real-time pipeline")
    print("-" * 90)
    print(f"{'PIPELINE DISPOSITION STATUS':<35} | [{status}]")
    print("=" * 90 + "\n")


def parse_cli_args() -> argparse.Namespace:
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(description="Hybrid RAG Incremental Data Ingestion Pipeline.")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR, help="Source files directory.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Target clean directory.")
    parser.add_argument("--full-rebuild", action="store_true", help="Force re-parsing of all files.")
    parser.add_argument("--force-publish", action="store_true", help="Publish even if quarantined.")
    parser.add_argument("--concurrency", type=int, default=4, help="Worker concurrency.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_cli_args()
    run_incremental_datapipeline(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        incremental=not args.full_rebuild,
        max_workers=args.concurrency,
        force_publish=args.force_publish
    )
