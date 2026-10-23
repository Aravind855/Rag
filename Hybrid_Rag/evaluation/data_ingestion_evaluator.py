"""Data Ingestion, Parsing & Cleaning Evaluator for Hybrid RAG.

Evaluates and compares raw source data in `d:\RAG\Datasource` against cleaned
markdown documents in `d:\RAG\cleaned_documents` across 5 core dimensions:
  A. File Coverage (inventory matching, missing/failed files)
  B. Content Completeness (PDF pages, DOCX tables/paragraphs, Excel sheets/rows, PPTX slides)
  C. Content Fidelity (entity IDs, currencies, limits, dates, percentages, policy rules)
  D. Cleaning Quality (heading preservation, table structure, code fence integrity)
  E. Output Integrity (empty output, duplication, metadata/frontmatter completeness, encoding)

All operations are written as pure procedural functions without classes.
All paths are dynamically resolved.
"""

import json
import logging
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Configure stdout and stderr to UTF-8 with replace fallback for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# File type inspection libraries
try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

try:
    import docx
except ImportError:
    docx = None

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    from pptx import Presentation
except ImportError:
    Presentation = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("hybrid_rag.evaluation.ingestion")

# =====================================================================
# DYNAMIC PATH RESOLUTION
# =====================================================================
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent

DATASOURCE_DIR = PROJECT_ROOT / "Datasource"
CLEANED_DIR = PROJECT_ROOT / "cleaned_documents"
MANIFEST_PATH = CLEANED_DIR / "cleaned_documents_manifest.json"
REPORTS_DIR = CURRENT_DIR / "reports"


# =====================================================================
# 1. FILE INVENTORY & COVERAGE CHECK (DIMENSION A)
# =====================================================================

def scan_source_inventory(source_dir: Path = DATASOURCE_DIR) -> Dict[str, Any]:
    """Scans all source documents and groups them by department category."""
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    all_files = [p for p in source_dir.rglob("*") if p.is_file()]
    inventory = {
        "total_source_files": len(all_files),
        "department_files": {},
        "meta_files": [],
        "extensions": {},
    }

    for f in all_files:
        ext = f.suffix.lower()
        inventory["extensions"][ext] = inventory["extensions"].get(ext, 0) + 1

        rel_path = f.relative_to(source_dir).as_posix()
        parts = rel_path.split("/")
        
        # Files at root (like readme.md) are meta/overview docs
        if len(parts) == 1:
            inventory["meta_files"].append(rel_path)
        else:
            category = parts[0]
            if category not in inventory["department_files"]:
                inventory["department_files"][category] = []
            inventory["department_files"][category].append({
                "relative_path": rel_path,
                "file_name": f.name,
                "extension": ext,
                "size_bytes": f.stat().st_size,
                "absolute_path": str(f),
            })

    return inventory


def evaluate_file_coverage(
    source_inventory: Dict[str, Any],
    manifest_data: Dict[str, Any],
    ) -> Dict[str, Any]:
    """Evaluates whether all supported source documents were processed and manifest-indexed."""
    cleaned_docs = manifest_data.get("documents", [])
    cleaned_source_paths = {d.get("source_path", "").replace("\\", "/") for d in cleaned_docs}

    expected_department_files: List[Dict[str, Any]] = []
    for cat, files in source_inventory["department_files"].items():
        expected_department_files.extend(files)

    processed_files = []
    missing_files = []

    for item in expected_department_files:
        rel = item["relative_path"]
        if rel in cleaned_source_paths:
            processed_files.append(rel)
        else:
            missing_files.append(rel)

    total_expected = len(expected_department_files)
    total_processed = len(processed_files)
    coverage_pct = round((total_processed / total_expected * 100), 2) if total_expected > 0 else 0.0

    return {
        "total_source_files_found": source_inventory["total_source_files"],
        "expected_department_documents": total_expected,
        "processed_documents": total_processed,
        "missing_documents": missing_files,
        "meta_or_root_documents": source_inventory["meta_files"],
        "file_coverage_pct": coverage_pct,
        "extraction_success_rate_pct": coverage_pct,
        "extension_breakdown": source_inventory["extensions"],
    }


# =====================================================================
# 2. CONTENT COMPLETENESS CHECK (DIMENSION B)
# =====================================================================

def inspect_raw_pdf(pdf_path: Path) -> Dict[str, Any]:
    """Directly inspects raw PDF ground truth page counts and extractable text."""
    if not fitz:
        return {"error": "pymupdf not installed"}

    doc = fitz.open(str(pdf_path))
    page_count = len(doc)
    total_chars = 0
    empty_pages = 0

    for pno in range(page_count):
        txt = doc[pno].get_text() or ""
        total_chars += len(txt.strip())
        if len(txt.strip()) == 0:
            empty_pages += 1

    doc.close()
    return {
        "page_count": page_count,
        "raw_text_chars": total_chars,
        "empty_pages": empty_pages,
    }


def inspect_raw_docx(docx_path: Path) -> Dict[str, Any]:
    """Directly inspects raw DOCX paragraphs and tables."""
    if not docx:
        return {"error": "python-docx not installed"}

    doc = docx.Document(str(docx_path))
    total_paragraphs = len(doc.paragraphs)
    total_tables = len(doc.tables)
    total_table_rows = sum(len(t.rows) for t in doc.tables)
    total_chars = sum(len(p.text) for p in doc.paragraphs)

    return {
        "paragraph_count": total_paragraphs,
        "table_count": total_tables,
        "table_row_count": total_table_rows,
        "raw_text_chars": total_chars,
    }


def inspect_raw_excel(xlsx_path: Path) -> Dict[str, Any]:
    """Directly inspects raw Excel worksheets, headers, and populated rows."""
    if not openpyxl:
        return {"error": "openpyxl not installed"}

    wb = openpyxl.load_workbook(str(xlsx_path), data_only=True, read_only=True)
    sheets = wb.sheetnames
    sheet_details = {}
    total_records = 0

    for s_name in sheets:
        sheet = wb[s_name]
        row_count = 0
        for row in sheet.iter_rows(values_only=True):
            if any(cell is not None for cell in row):
                row_count += 1
        # Data rows (excluding header)
        data_rows = max(0, row_count - 1)
        total_records += data_rows
        sheet_details[s_name] = {"total_rows": row_count, "data_rows": data_rows}

    wb.close()
    return {
        "sheet_count": len(sheets),
        "sheet_names": sheets,
        "total_records": total_records,
        "sheet_details": sheet_details,
    }


def inspect_raw_pptx(pptx_path: Path) -> Dict[str, Any]:
    """Directly inspects raw PowerPoint slides and text shapes."""
    if not Presentation:
        return {"error": "python-pptx not installed"}

    prs = Presentation(str(pptx_path))
    slide_count = len(prs.slides)
    total_shapes = 0
    total_chars = 0

    for slide in prs.slides:
        for shape in slide.shapes:
            total_shapes += 1
            if shape.has_text_frame:
                total_chars += sum(len(p.text) for p in shape.text_frame.paragraphs)

    return {
        "slide_count": slide_count,
        "shape_count": total_shapes,
        "raw_text_chars": total_chars,
    }


def evaluate_content_completeness(
    source_dir: Path,
    manifest_data: Dict[str, Any],
    cleaned_dir: Path,
) -> Dict[str, Any]:
    """Compares structural units (pages, rows, slides, tables) between raw sources and cleaned output."""
    cleaned_docs = manifest_data.get("documents", [])
    completeness_records = []
    
    total_expected_units = 0
    total_extracted_units = 0

    for doc in cleaned_docs:
        source_rel = doc.get("source_path", "").replace("\\", "/")
        source_abs = source_dir / source_rel
        clean_file = cleaned_dir / doc.get("clean_file", "")
        ext = source_abs.suffix.lower()

        clean_content = ""
        if clean_file.exists():
            clean_content = clean_file.read_text(encoding="utf-8", errors="replace")

        record = {
            "source_path": source_rel,
            "format": ext,
            "status": "PASS",
            "discrepancies": [],
        }

        if ext == ".pdf":
            raw_pdf = inspect_raw_pdf(source_abs)
            expected_pages = raw_pdf.get("page_count", 0)
            manifest_pages = doc.get("metadata", {}).get("total_pages", 0)

            total_expected_units += expected_pages
            total_extracted_units += manifest_pages

            record["expected_pages"] = expected_pages
            record["extracted_pages"] = manifest_pages
            if expected_pages != manifest_pages:
                record["status"] = "FAIL"
                record["discrepancies"].append(f"Page mismatch: raw {expected_pages} vs clean {manifest_pages}")

        elif ext == ".docx":
            raw_docx = inspect_raw_docx(source_abs)
            expected_tables = raw_docx.get("table_count", 0)
            manifest_tables = doc.get("metadata", {}).get("table_count", 0)

            total_expected_units += expected_tables
            total_extracted_units += manifest_tables

            record["expected_tables"] = expected_tables
            record["extracted_tables"] = manifest_tables
            if expected_tables != manifest_tables:
                record["status"] = "WARN"
                record["discrepancies"].append(f"Table count: raw {expected_tables} vs clean {manifest_tables}")

        elif ext == ".xlsx":
            raw_excel = inspect_raw_excel(source_abs)
            expected_sheets = raw_excel.get("sheet_count", 0)
            manifest_sheets = doc.get("metadata", {}).get("total_sheets", 0)
            expected_records = raw_excel.get("total_records", 0)
            manifest_records = doc.get("metadata", {}).get("total_records", 0)

            total_expected_units += expected_sheets
            total_extracted_units += manifest_sheets

            record["expected_sheets"] = expected_sheets
            record["extracted_sheets"] = manifest_sheets
            record["expected_records"] = expected_records
            record["extracted_records"] = manifest_records

            # Check each sheet name appears in cleaned markdown
            for sname in raw_excel.get("sheet_names", []):
                if sname not in clean_content:
                    record["discrepancies"].append(f"Worksheet '{sname}' header missing in markdown")
                    record["status"] = "FAIL"

        elif ext == ".pptx":
            raw_pptx = inspect_raw_pptx(source_abs)
            expected_slides = raw_pptx.get("slide_count", 0)
            manifest_slides = doc.get("metadata", {}).get("slide_count", 0)

            total_expected_units += expected_slides
            total_extracted_units += manifest_slides

            record["expected_slides"] = expected_slides
            record["extracted_slides"] = manifest_slides
            if expected_slides != manifest_slides:
                record["status"] = "FAIL"
                record["discrepancies"].append(f"Slide count: raw {expected_slides} vs clean {manifest_slides}")

        elif ext in (".md", ".txt", ".json"):
            # Check non-empty content
            raw_chars = len(source_abs.read_text(encoding="utf-8", errors="replace").strip())
            clean_chars = len(clean_content.strip())
            total_expected_units += 1
            total_extracted_units += 1 if clean_chars > 0 else 0

            record["raw_chars"] = raw_chars
            record["clean_chars"] = clean_chars
            if clean_chars < (raw_chars * 0.7):
                record["status"] = "WARN"
                record["discrepancies"].append(f"Clean text length {clean_chars} is significantly lower than raw {raw_chars}")

        completeness_records.append(record)

    coverage_pct = round((total_extracted_units / total_expected_units * 100), 2) if total_expected_units > 0 else 100.0

    return {
        "content_extraction_coverage_pct": coverage_pct,
        "total_structural_units_expected": total_expected_units,
        "total_structural_units_extracted": total_extracted_units,
        "records": completeness_records,
    }


# =====================================================================
# 3. CONTENT FIDELITY CHECK (DIMENSION C)
# =====================================================================

CRITICAL_DOMAIN_GROUND_TRUTH = [
    # Engineering & Architecture IDs and Standards
    {"entity": "NC-ENG-API-2026-08", "type": "Document_ID", "expected_file": "engineering/api_standards.md"},
    {"entity": "PROJECT_NOT_FOUND", "type": "Error_Code", "expected_file": "engineering/api_standards.md"},
    {"entity": "SCREAMING_SNAKE_CASE", "type": "Naming_Rule", "expected_file": "engineering/api_standards.md"},
    {"entity": "SYS-001", "type": "System_ID", "expected_file": "operations/system_catalog.json"},
    {"entity": "SYS-002", "type": "System_ID", "expected_file": "operations/system_catalog.json"},
    {"entity": "NC-OPS-VND-2026-08", "type": "Document_ID", "expected_file": "operations/vendor_management.docx"},
    {"entity": "NC-SEC-ACL-2026-08", "type": "Document_ID", "expected_file": "security/access_control.md"},
    {"entity": "NC-SEC-IR-2026-08", "type": "Document_ID", "expected_file": "security/incident_response.txt"},

    # Travel & Reimbursement Limits and Codes
    {"entity": "TRV-AIR", "type": "Category_Code", "expected_file": "finance/expense_categories.xlsx"},
    {"entity": "TRV-HOT", "type": "Category_Code", "expected_file": "finance/expense_categories.xlsx"},
    {"entity": "INR 6,500", "type": "Currency_Limit", "expected_file": "hr/employee_handbook(1).pdf"},
    {"entity": "INR 1,200", "type": "Currency_Limit", "expected_file": "hr/employee_handbook(1).pdf"},
    {"entity": "INR 3,500", "type": "Currency_Limit", "expected_file": "finance/expense_policy.pdf"},
    {"entity": "INR 1,000", "type": "Threshold_Limit", "expected_file": "finance/expense_categories.xlsx"},
    {"entity": "INR 2,000", "type": "Gift_Limit", "expected_file": "hr/employee_handbook(1).pdf"},

    # SLA & Operational Numbers
    {"entity": "99.95%", "type": "SLA_Percentage", "expected_file": "operations/system_catalog.json"},
    {"entity": "99.9%", "type": "SLA_Percentage", "expected_file": "operations/system_catalog.json"},
    {"entity": "15 minutes", "type": "Time_SLA", "expected_file": "operations/system_catalog.json"},
    {"entity": "3 business days", "type": "Booking_Window", "expected_file": "finance/expense_policy.pdf"},
    {"entity": "7 business days", "type": "Booking_Window", "expected_file": "finance/expense_policy.pdf"},

    # Critical Policy Negations & Directives
    {"entity": "prohibited", "type": "Policy_Directive", "expected_file": "finance/expense_policy.pdf"},
    {"entity": "non-refundable", "type": "Policy_Directive", "expected_file": "finance/expense_policy.pdf"},
    {"entity": "mandatory", "type": "Policy_Directive", "expected_file": "finance/expense_policy.pdf"},
]


def evaluate_content_fidelity(cleaned_dir: Path = CLEANED_DIR) -> Dict[str, Any]:
    """Verifies that mission-critical IDs, values, SLAs, and policy rules survived extraction."""
    # Build complete text lookup per cleaned category/document
    cleaned_texts = {}
    for f in cleaned_dir.rglob("*.md"):
        rel = f.relative_to(cleaned_dir).as_posix()
        cleaned_texts[rel] = f.read_text(encoding="utf-8", errors="replace")

    all_combined_text = "\n".join(cleaned_texts.values())

    results = []
    passed_count = 0

    for item in CRITICAL_DOMAIN_GROUND_TRUTH:
        val = item["entity"]
        val_type = item["type"]
        exp_file = item["expected_file"]
        
        # Determine cleaned target filename
        clean_target = exp_file.replace(".docx", ".md").replace(".xlsx", ".md").replace(".pptx", ".md").replace(".pdf", ".md").replace(".txt", ".md").replace(".json", ".md")
        clean_target = clean_target.replace("(1)", "")  # normalized names

        # Search specifically in target document or across all cleaned documents
        found_in_target = False
        target_content = ""
        for k, text in cleaned_texts.items():
            if Path(k).name == Path(clean_target).name or Path(k).stem in clean_target:
                target_content = text
                if val.lower() in text.lower():
                    found_in_target = True
                    break

        found_anywhere = val.lower() in all_combined_text.lower()
        success = found_in_target or found_anywhere
        if success:
            passed_count += 1

        results.append({
            "entity": val,
            "type": val_type,
            "expected_file": exp_file,
            "matched_in_target": found_in_target,
            "matched_in_corpus": found_anywhere,
            "status": "PASS" if success else "FAIL",
        })

    accuracy_pct = round((passed_count / len(CRITICAL_DOMAIN_GROUND_TRUTH) * 100), 2)

    return {
        "critical_field_accuracy_pct": accuracy_pct,
        "total_critical_fields_tested": len(CRITICAL_DOMAIN_GROUND_TRUTH),
        "fields_preserved": passed_count,
        "fields_missing": len(CRITICAL_DOMAIN_GROUND_TRUTH) - passed_count,
        "field_results": results,
    }


# =====================================================================
# 4. CLEANING QUALITY & STRUCTURE CHECK (DIMENSION D)
# =====================================================================

def evaluate_cleaning_quality(cleaned_dir: Path = CLEANED_DIR) -> Dict[str, Any]:
    """Inspects markdown quality: table formatting, code fences, headers, and absence of noise."""
    cleaned_files = list(cleaned_dir.rglob("*.md"))
    quality_records = []
    
    total_tables_checked = 0
    valid_tables = 0
    total_headings_checked = 0
    valid_headings = 0
    code_blocks_checked = 0
    balanced_code_blocks = 0

    for f in cleaned_files:
        rel = f.relative_to(cleaned_dir).as_posix()
        content = f.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()

        file_issues = []

        # 1. Heading verification
        for line in lines:
            if line.startswith("#"):
                total_headings_checked += 1
                if re.match(r"^#{1,6}\s+.+", line):
                    valid_headings += 1
                else:
                    file_issues.append(f"Malformed heading syntax: '{line[:40]}'")

        # 2. Table delimiter and structure verification
        table_delimiters = [i for i, line in enumerate(lines) if re.match(r"^\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?$", line)]
        for idx in table_delimiters:
            total_tables_checked += 1
            if idx > 0 and "|" in lines[idx - 1]:
                header_cols = len([c for c in lines[idx - 1].split("|") if c.strip()])
                delim_cols = len([c for c in lines[idx].split("|") if c.strip()])
                if header_cols == delim_cols:
                    valid_tables += 1
                else:
                    file_issues.append(f"Table column mismatch at line {idx}: header ({header_cols}) vs delimiter ({delim_cols})")
            else:
                file_issues.append(f"Table delimiter without header at line {idx}")

        # 3. Code fence balance
        code_fences = [line for line in lines if line.strip().startswith("```")]
        code_blocks_checked += len(code_fences) // 2
        if len(code_fences) % 2 == 0:
            balanced_code_blocks += len(code_fences) // 2
        else:
            file_issues.append(f"Unbalanced code block fences (found {len(code_fences)} fence markers)")

        quality_records.append({
            "clean_file": rel,
            "total_lines": len(lines),
            "table_count": len(table_delimiters),
            "issues": file_issues,
            "status": "PASS" if not file_issues else "WARN",
        })

    heading_integrity_pct = round((valid_headings / total_headings_checked * 100), 2) if total_headings_checked > 0 else 100.0
    table_integrity_pct = round((valid_tables / total_tables_checked * 100), 2) if total_tables_checked > 0 else 100.0

    return {
        "heading_integrity_pct": heading_integrity_pct,
        "table_integrity_pct": table_integrity_pct,
        "total_headings_checked": total_headings_checked,
        "total_tables_checked": total_tables_checked,
        "code_blocks_checked": code_blocks_checked,
        "balanced_code_blocks": balanced_code_blocks,
        "records": quality_records,
    }


# =====================================================================
# 5. OUTPUT INTEGRITY & METADATA CHECK (DIMENSION E)
# =====================================================================

def evaluate_output_integrity(
    cleaned_dir: Path = CLEANED_DIR,
    manifest_path: Path = MANIFEST_PATH,
) -> Dict[str, Any]:
    """Validates manifest completeness, frontmatter presence, encoding, empty and duplicate files."""
    if not manifest_path.exists():
        return {"error": "Manifest file not found"}

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    docs = manifest.get("documents", [])
    total_docs = len(docs)

    empty_docs = []
    duplicate_docs = []
    missing_metadata_docs = []
    encoding_error_docs = []

    seen_sources = set()
    required_meta_keys = {"file_name", "category", "document_type", "breadcrumbs", "source"}

    for doc in docs:
        src = doc.get("source_path", "")
        clean_file_rel = doc.get("clean_file", "")
        clean_path = cleaned_dir / clean_file_rel

        # Check Duplication
        if src in seen_sources:
            duplicate_docs.append(src)
        seen_sources.add(src)

        # Check Empty Output
        if not clean_path.exists() or clean_path.stat().st_size == 0 or doc.get("total_words", 0) == 0:
            empty_docs.append(clean_file_rel)

        # Check Metadata Completeness
        meta = doc.get("metadata", {})
        missing_keys = required_meta_keys - set(meta.keys())
        if missing_keys:
            missing_metadata_docs.append({"file": clean_file_rel, "missing_keys": list(missing_keys)})

        # Check Encoding
        if clean_path.exists():
            try:
                raw_bytes = clean_path.read_bytes()
                raw_bytes.decode("utf-8")
                # Look for unicode replacement char
                if b"\xef\xbf\xbd" in raw_bytes:
                    encoding_error_docs.append(clean_file_rel)
            except UnicodeDecodeError:
                encoding_error_docs.append(clean_file_rel)

    empty_output_rate_pct = round((len(empty_docs) / total_docs * 100), 2) if total_docs > 0 else 0.0
    duplicate_rate_pct = round((len(duplicate_docs) / total_docs * 100), 2) if total_docs > 0 else 0.0
    metadata_completeness_pct = round(((total_docs - len(missing_metadata_docs)) / total_docs * 100), 2) if total_docs > 0 else 100.0

    return {
        "total_cleaned_documents": total_docs,
        "empty_output_rate_pct": empty_output_rate_pct,
        "duplicate_rate_pct": duplicate_rate_pct,
        "metadata_completeness_pct": metadata_completeness_pct,
        "empty_documents": empty_docs,
        "duplicate_documents": duplicate_docs,
        "missing_metadata_documents": missing_metadata_docs,
        "encoding_error_documents": encoding_error_docs,
    }


# =====================================================================
# 6. COMPREHENSIVE PIPELINE EVALUATION RUNNER
# =====================================================================

def run_data_ingestion_evaluation(
    source_dir: Path = DATASOURCE_DIR,
    cleaned_dir: Path = CLEANED_DIR,
    manifest_path: Path = MANIFEST_PATH,
    export_report: bool = True,
) -> Dict[str, Any]:
    """Executes all 5 evaluation dimensions, computes standardized metrics, and saves report."""
    start_time = time.time()
    logger.info("=" * 80)
    logger.info("STARTING DATA INGESTION, PARSING & CLEANING EVALUATION")
    logger.info(f"Source Directory:  {source_dir}")
    logger.info(f"Cleaned Directory: {cleaned_dir}")
    logger.info(f"Manifest Path:     {manifest_path}")
    logger.info("=" * 80)

    # 1. Load Manifest
    if not manifest_path.exists():
        raise FileNotFoundError(f"Cleaned manifest not found: {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    # 2. Run Individual Evaluation Dimensions
    source_inv = scan_source_inventory(source_dir)
    dim_a = evaluate_file_coverage(source_inv, manifest_data)
    dim_b = evaluate_content_completeness(source_dir, manifest_data, cleaned_dir)
    dim_c = evaluate_content_fidelity(cleaned_dir)
    dim_d = evaluate_cleaning_quality(cleaned_dir)
    dim_e = evaluate_output_integrity(cleaned_dir, manifest_path)

    # 3. Compile Executive Scorecard
    metrics_summary = {
        "File Coverage (%)": dim_a["file_coverage_pct"],
        "Extraction Success Rate (%)": dim_a["extraction_success_rate_pct"],
        "Content Extraction Coverage (%)": dim_b["content_extraction_coverage_pct"],
        "Critical Field Accuracy (%)": dim_c["critical_field_accuracy_pct"],
        "Heading Integrity (%)": dim_d["heading_integrity_pct"],
        "Table Integrity (%)": dim_d["table_integrity_pct"],
        "Metadata Completeness (%)": dim_e["metadata_completeness_pct"],
        "Empty Output Rate (%)": dim_e["empty_output_rate_pct"],
        "Duplicate Rate (%)": dim_e["duplicate_rate_pct"],
    }

    # Pass / Fail overall grade
    passed_core = (
        dim_a["file_coverage_pct"] >= 95.0
        and dim_b["content_extraction_coverage_pct"] >= 95.0
        and dim_c["critical_field_accuracy_pct"] >= 95.0
        and dim_e["empty_output_rate_pct"] == 0.0
        and dim_e["duplicate_rate_pct"] == 0.0
    )
    overall_status = "PASS" if passed_core else "FAIL"

    elapsed_s = round(time.time() - start_time, 2)

    full_report = {
        "evaluation_name": "Data Ingestion, Parsing & Cleaning Evaluation",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "overall_status": overall_status,
        "elapsed_seconds": elapsed_s,
        "scorecard": metrics_summary,
        "dimension_a_file_coverage": dim_a,
        "dimension_b_content_completeness": dim_b,
        "dimension_c_content_fidelity": dim_c,
        "dimension_d_cleaning_quality": dim_d,
        "dimension_e_output_integrity": dim_e,
    }

    # 4. Save JSON Report Artifact
    if export_report:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_file = REPORTS_DIR / "data_ingestion_evaluation_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(full_report, f, indent=2)
        logger.info(f"Evaluation report exported successfully to: {report_file}")

    return full_report


def print_evaluation_summary(report: Dict[str, Any]):
    """Prints a beautiful, formatted summary of the evaluation results in the terminal."""
    sc = report["scorecard"]
    print("\n" + "=" * 95)
    print("DATA INGESTION, PARSING & CLEANING EVALUATION SCORECARD")
    print("=" * 95)
    print(f"{'Metric Name':<38} | {'Measured Value':<16} | {'Target Benchmark':<18} | {'Status'}")
    print("-" * 95)

    benchmarks = [
        ("File Coverage (%)", f"{sc['File Coverage (%)']}%", "100.0%", sc['File Coverage (%)'] >= 95.0),
        ("Extraction Success Rate (%)", f"{sc['Extraction Success Rate (%)']}%", "100.0%", sc['Extraction Success Rate (%)'] >= 95.0),
        ("Content Extraction Coverage (%)", f"{sc['Content Extraction Coverage (%)']}%", ">= 95.0%", sc['Content Extraction Coverage (%)'] >= 95.0),
        ("Critical Field Accuracy (%)", f"{sc['Critical Field Accuracy (%)']}%", "100.0%", sc['Critical Field Accuracy (%)'] >= 95.0),
        ("Heading Integrity (%)", f"{sc['Heading Integrity (%)']}%", "100.0%", sc['Heading Integrity (%)'] >= 98.0),
        ("Table Integrity (%)", f"{sc['Table Integrity (%)']}%", "100.0%", sc['Table Integrity (%)'] >= 95.0),
        ("Metadata Completeness (%)", f"{sc['Metadata Completeness (%)']}%", "100.0%", sc['Metadata Completeness (%)'] == 100.0),
        ("Empty Output Rate (%)", f"{sc['Empty Output Rate (%)']}%", "0.0%", sc['Empty Output Rate (%)'] == 0.0),
        ("Duplicate Rate (%)", f"{sc['Duplicate Rate (%)']}%", "0.0%", sc['Duplicate Rate (%)'] == 0.0),
    ]

    for name, val, target, passed in benchmarks:
        status_label = "[PASS]" if passed else "[WARN/FAIL]"
        print(f"{name:<38} | {val:<16} | {target:<18} | {status_label}")

    print("-" * 95)
    print(f"OVERALL EVALUATION GRADE: {report['overall_status']} (Completed in {report['elapsed_seconds']}s)")
    print("=" * 95 + "\n")


if __name__ == "__main__":
    report = run_data_ingestion_evaluation()
    print_evaluation_summary(report)
