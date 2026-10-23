"""Pipeline Health & Observability Telemetry Monitor (Functional Approach).

Located in d:\\RAG\\Hybrid_Rag\\data_ingestion\\incremental_ingestion_monitor.py
Inspects durable ingestion state, manifests, quarantine queues, and published deltas
to generate comprehensive audit trails and operational dashboards for Hybrid RAG.

Strictly procedural (zero classes). All paths resolved dynamically.
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

# UTF-8 terminal safety for Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("hybrid_rag.ingestion_monitor")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLEANED_DIR = PROJECT_ROOT / "cleaned_documents"
STATE_FILE = CLEANED_DIR / "ingestion_state.json"
MANIFEST_FILE = CLEANED_DIR / "cleaned_documents_manifest.json"
DELTA_FILE = CLEANED_DIR / "published_delta.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "evaluation" / "reports"


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Safely loads JSON from a file, returning empty dict if missing."""
    if file_path.exists():
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Error reading JSON from {file_path}: {e}")
    return {}


def run_pipeline_telemetry_monitor() -> Dict[str, Any]:
    """Generates an operational health dashboard and writes an audit log."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    state = load_json_file(STATE_FILE)
    manifest = load_json_file(MANIFEST_FILE)
    delta = load_json_file(DELTA_FILE)

    entries = state.get("entries", {})
    total_tracked = len(entries)

    published = [k for k, v in entries.items() if v.get("disposition") == "PUBLISH"]
    quarantined = [k for k, v in entries.items() if v.get("disposition") == "QUARANTINE"]
    failed = [k for k, v in entries.items() if v.get("disposition") == "FAIL"]

    quality_scores = [v.get("quality_score", 0.0) for v in entries.values() if "quality_score" in v]
    avg_quality = round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else 100.0

    dept_counts: Dict[str, int] = {}
    for doc in manifest.get("documents", []):
        cat = doc.get("category", "general")
        dept_counts[cat] = dept_counts.get(cat, 0) + 1

    health_status = "HEALTHY" if not failed and not quarantined else "NEEDS_ATTENTION"

    audit_report = {
        "report_name": "Hybrid RAG Ingestion Pipeline Health & Observability Audit",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "health_status": health_status,
        "metrics": {
            "total_tracked_files": total_tracked,
            "published_active_files": len(published),
            "quarantined_files": len(quarantined),
            "failed_files": len(failed),
            "average_quality_score_pct": avg_quality,
            "total_clean_words": manifest.get("total_words", 0),
            "total_clean_characters": manifest.get("total_characters", 0),
            "total_clean_tables": manifest.get("total_tables", 0),
            "department_document_distribution": dept_counts,
        },
        "recent_delta": {
            "delta_timestamp": delta.get("timestamp"),
            "delta_files_count": delta.get("total_delta_files", 0),
        },
        "quarantined_details": [
            {"path": k, "reasons": entries[k].get("validation_reasons")} for k in quarantined
        ],
        "failed_details": [
            {"path": k, "error": entries[k].get("error_message")} for k in failed
        ],
    }

    audit_file = REPORTS_DIR / "pipeline_run_audit.json"
    audit_file.write_text(json.dumps(audit_report, indent=2), encoding="utf-8")
    logger.info(f"Pipeline audit trail exported to: {audit_file}")

    # Output Terminal Scorecard
    print_telemetry_dashboard(audit_report)

    return audit_report


def print_telemetry_dashboard(report: Dict[str, Any]) -> None:
    """Prints a beautiful operational dashboard."""
    m = report["metrics"]
    print("\n" + "=" * 90)
    print("HYBRID RAG PIPELINE OBSERVABILITY & HEALTH DASHBOARD")
    print("=" * 90)
    print(f"{'Operational Metric':<35} | {'Measured Value':<22} | {'Target Benchmark':<20}")
    print("-" * 90)
    print(f"{'Active Tracked Documents':<35} | {m['total_tracked_files']:<22} | Stable Catalog")
    print(f"{'Published Active Documents':<35} | {m['published_active_files']:<22} | 100% Retrievable")
    print(f"{'Quarantined Documents (Suspicious)':<35} | {m['quarantined_files']:<22} | 0 target")
    print(f"{'Dead-Letter Queue Failures':<35} | {m['failed_files']:<22} | 0 target")
    print(f"{'Average Pipeline Quality Score':<35} | {m['average_quality_score_pct']}%                | >= 95.0%")
    print(f"{'Total Ingested Words':<35} | {m['total_clean_words']:,} words           | Complete corpus")
    print(f"{'Total Ingested Tables':<35} | {m['total_clean_tables']} tables             | Structure intact")
    print("-" * 90)
    print(f"{'PIPELINE SYSTEM HEALTH':<35} | [{report['health_status']}]")
    print("=" * 90)

    print("\nDEPARTMENT DOCUMENT DISTRIBUTION:")
    for dept, count in sorted(m["department_document_distribution"].items()):
        print(f" * {dept:<16}: {count} published documents")
    print("=" * 90 + "\n")


if __name__ == "__main__":
    run_pipeline_telemetry_monitor()
