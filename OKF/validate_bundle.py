#!/usr/bin/env python3
"""
OKF (Open Knowledge Format v0.2) Official Specification Bundle Validator
Validates blocking specification errors and quality warnings matching the official OKF validator.
"""

import sys
import re
from pathlib import Path
from datetime import datetime
import yaml

FRONTMATTER_REGEX = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
ISO_UTC_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")

def parse_okf_file(file_path: Path):
    content = file_path.read_text(encoding="utf-8")
    match = FRONTMATTER_REGEX.match(content)
    if not match:
        return None, content
    yaml_text, markdown_body = match.groups()
    try:
        data = yaml.safe_load(yaml_text) or {}
        return data, markdown_body
    except yaml.YAMLError as err:
        return {"_yaml_error": str(err)}, markdown_body

def validate_bundle(bundle_dir: Path):
    print(f"\n==================================================")
    print(f" Validating OKF Bundle: {bundle_dir.resolve()}")
    print(f"==================================================")
    
    errors = []
    warnings = []
    scanned_md_count = 0
    concept_count = 0

    # 1. Check Root index.md
    root_index = bundle_dir / "index.md"
    if not root_index.exists():
        errors.append("index.md (OKF_bundle): Missing root 'index.md' catalog.")
    else:
        scanned_md_count += 1
        meta, body = parse_okf_file(root_index)
        if meta is None or "okf_version" not in meta:
            errors.append("index.md (OKF_bundle): Root index.md must contain frontmatter declaring okf_version.")
        else:
            # Check for illegal extra frontmatter fields
            extra_keys = set(meta.keys()) - {"okf_version"}
            if extra_keys:
                errors.append(f"index.md (OKF_bundle): reserved frontmatter forbidden: Only 'okf_version' permitted in root index.md frontmatter. Found extra: {extra_keys}")

        # Check reserved index structure
        has_heading = bool(re.search(r"^#+\s+.+", body, re.MULTILINE))
        has_list_link = bool(re.search(r"^\s*[\*\-]\s+\[.*?\]\(.*?\)", body, re.MULTILINE))
        if not (has_heading and has_list_link):
            errors.append("index.md (OKF_bundle): reserved index structure: index.md must contain at least one heading and one Markdown list entry linking to a concept or subdirectory.")

    # 2. Check Root log.md
    root_log = bundle_dir / "log.md"
    if root_log.exists():
        scanned_md_count += 1
        meta, _ = parse_okf_file(root_log)
        if meta is not None:
            errors.append("log.md (OKF_bundle): reserved frontmatter forbidden: Frontmatter is not permitted in log.md.")
    else:
        warnings.append("log.md (OKF_bundle): Missing 'log.md' audit changelog.")

    # 3. Check All Files
    for path in sorted(bundle_dir.rglob("*.md")):
        if path == root_index or path == root_log:
            continue

        scanned_md_count += 1
        rel_path = path.relative_to(bundle_dir).as_posix()

        # Check for forbidden nested index.md
        if path.name == "index.md":
            errors.append(f"{rel_path}: reserved frontmatter forbidden: Nested index.md files are forbidden.")
            continue

        concept_count += 1
        meta, body = parse_okf_file(path)

        if meta is None:
            errors.append(f"{rel_path}: Missing YAML frontmatter delimiters (---).")
            continue
        if "_yaml_error" in meta:
            errors.append(f"{rel_path}: Invalid YAML syntax: {meta['_yaml_error']}")
            continue

        # Mandatory Rule: Non-empty type
        concept_type = meta.get("type")
        if not concept_type or not str(concept_type).strip():
            errors.append(f"{rel_path}: Mandatory field 'type' is missing or empty.")

        # Quality Warnings
        # 1. Description missing
        desc = meta.get("description")
        if not desc or not str(desc).strip():
            warnings.append(f"{rel_path}: description missing - Add a short description that explains the concept in plain language.")

        # 2. Tags missing
        tags = meta.get("tags")
        if not tags or not isinstance(tags, list) or len(tags) == 0:
            warnings.append(f"{rel_path}: tags missing - Add tags as a YAML array.")

        # 3. Sources entries must be mappings with at least 'resource'
        sources = meta.get("sources")
        if sources:
            if not isinstance(sources, list):
                warnings.append(f"{rel_path}: sources must be a YAML list.")
            else:
                for idx, src in enumerate(sources, start=1):
                    if not isinstance(src, dict):
                        warnings.append(f"{rel_path}: source not map - Entry {idx} should be a YAML mapping with at least a 'resource' field.")
                    elif "resource" not in src:
                        warnings.append(f"{rel_path}: source missing resource - Entry {idx} mapping missing 'resource' field.")

        # 4. stale_after must be ISO 8601 with UTC offset
        stale_after = meta.get("stale_after")
        if stale_after:
            if not ISO_UTC_REGEX.match(str(stale_after).strip()):
                warnings.append(f"{rel_path}: stale after invalid - stale_after should be an ISO 8601 datetime with a UTC offset (e.g. 2027-08-01T00:00:00Z).")

    # Output Summary
    print(f"\nScan Summary:")
    print(f"- Markdown files scanned: {scanned_md_count}")
    print(f"- Concept files checked : {concept_count}")
    print(f"- Errors found           : {len(errors)}")
    print(f"- Warnings found         : {len(warnings)}")
    print("-" * 50)

    if errors:
        print("\n[BLOCKING ERRORS]:")
        for e in errors:
            print(f"  [ERROR] {e}")

    if warnings:
        print("\n[QUALITY WARNINGS]:")
        for w in warnings:
            print(f"  [WARN] {w}")

    if not errors and not warnings:
        print("\n[SUCCESS] OKF Bundle is 100% compliant! (0 errors, 0 warnings)")
        return True
    elif not errors:
        print(f"\n[PASS] No blocking errors! ({len(warnings)} quality warning(s) remaining)")
        return True
    else:
        print(f"\n[FAIL] Validation failed with {len(errors)} blocking error(s).")
        return False

if __name__ == "__main__":
    bundle_path = Path("d:/RAG/OKF/OKF_bundle")
    success = validate_bundle(bundle_path)
    sys.exit(0 if success else 1)
