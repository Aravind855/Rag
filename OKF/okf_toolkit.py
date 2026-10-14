"""
OKF (Open Knowledge Format v0.2) Bundle Toolkit.

Provides machine-readable exploration, retrieval, and trust inspection
tools over an OKF v0.2 knowledge bundle without chunking or vector databases.
"""

import os
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import yaml

FRONTMATTER_REGEX = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


class OKFBundleToolkit:
    """Core toolkit to navigate, search, and retrieve from an OKF v0.2 bundle."""

    def __init__(self, bundle_dir: str = "d:/RAG/OKF/OKF_bundle"):
        self.bundle_dir = Path(bundle_dir).resolve()
        if not self.bundle_dir.exists():
            raise FileNotFoundError(f"OKF bundle directory not found at: {self.bundle_dir}")
        self._index_cache: Dict[str, Dict[str, Any]] = {}
        self._build_concept_cache()

    def _build_concept_cache(self):
        """Scans the bundle and caches all concept IDs, paths, and frontmatter metadata."""
        self._index_cache.clear()
        for md_path in self.bundle_dir.rglob("*.md"):
            rel_path = md_path.relative_to(self.bundle_dir).as_posix()
            meta, body = self._parse_file(md_path)
            if not meta and md_path.name != "index.md" and md_path.name != "log.md":
                continue

            concept_id = meta.get("id") if meta else None
            if not concept_id:
                if md_path.name == "index.md":
                    concept_id = "index.root"
                elif md_path.name == "log.md":
                    concept_id = "log.changelog"
                else:
                    concept_id = rel_path

            # Normalize verification tier
            verified_val = meta.get("verified") if meta else None
            if isinstance(verified_val, dict):
                verified_str = f"verified by {verified_val.get('by', 'authorized verifier')}"
            elif isinstance(verified_val, str):
                verified_str = verified_val
            else:
                verified_str = meta.get("trust", {}).get("verified", "unverified") if meta else "unverified"

            self._index_cache[concept_id] = {
                "id": concept_id,
                "path": rel_path,
                "abs_path": md_path,
                "metadata": meta or {},
                "title": meta.get("title", md_path.stem) if meta else md_path.stem,
                "type": meta.get("type", "concept") if meta else "catalog",
                "description": meta.get("description", "") if meta else "",
                "status": meta.get("status", "unknown") if meta else "active",
                "verified": verified_str,
                "stale_after": meta.get("stale_after") if meta else None,
                "summary": body.strip().split("\n\n")[0] if body else ""
            }

    def _parse_file(self, file_path: Path):
        content = file_path.read_text(encoding="utf-8")
        match = FRONTMATTER_REGEX.match(content)
        if not match:
            return {}, content
        yaml_text, markdown_body = match.groups()
        try:
            data = yaml.safe_load(yaml_text) or {}
            return data, markdown_body
        except yaml.YAMLError:
            return {}, markdown_body

    def browse_catalog(self, domain: Optional[str] = None) -> str:
        """Browse the OKF root catalog or a specific domain section."""
        root_index = self.bundle_dir / "index.md"
        if not root_index.exists():
            return "Error: Root index.md not found in bundle."

        content = root_index.read_text(encoding="utf-8")
        if not domain or domain.strip().lower() in ["", "root", "all"]:
            return content

        # Extract specific domain section (e.g. # Engineering)
        d_name = domain.strip().lower()
        sections = re.split(r"(?m)^#\s+", content)
        for sec in sections:
            lines = sec.strip().split("\n")
            if lines and lines[0].strip().lower() == d_name:
                return f"# {sec.strip()}"

        return content

    def find_concepts(self, query: str, concept_type: Optional[str] = None) -> str:
        """Search across concept IDs, titles, types, tags, descriptions, and body content."""
        q = query.strip().lower()
        results = []
        query_words = [w for w in q.split() if len(w) > 2]

        for cid, info in self._index_cache.items():
            if info["path"] in ["index.md", "log.md"]:
                continue

            if concept_type and info["type"].lower() != concept_type.strip().lower():
                continue

            meta = info["metadata"]
            _, body = self._parse_file(info["abs_path"])
            tags_str = " ".join(meta.get("tags", []))
            desc_str = meta.get("description", "")

            searchable_text = f"{cid} {info['title']} {info['type']} {tags_str} {desc_str} {body}".lower()

            matched = False
            match_reason = ""

            if q in searchable_text:
                matched = True
                match_reason = "Full phrase match"
            elif any(w in searchable_text for w in query_words):
                matched_count = sum(1 for w in query_words if w in searchable_text)
                if matched_count >= max(1, len(query_words) // 2):
                    matched = True
                    match_reason = f"Keyword match ({matched_count}/{len(query_words)} terms)"

            if matched:
                results.append((info, match_reason))

        if not results:
            return f"No concepts matching '{query}' (type filter: '{concept_type or 'all'}')."

        output = [f"Found {len(results)} matching concept(s):"]
        for info, reason in results:
            output.append(
                f"- Concept ID: `{info['id']}`\n"
                f"  Title: {info['title']}\n"
                f"  Type: {info['type']} | Status: {info['status']} | Verified: {info['verified']}\n"
                f"  Path: {info['path']} ({reason})"
            )
        return "\n\n".join(output)

    def read_concept(self, concept_id_or_path: str) -> str:
        """Retrieve the complete, exact content of an OKF concept (frontmatter + Markdown)."""
        target_info = None

        if concept_id_or_path in self._index_cache:
            target_info = self._index_cache[concept_id_or_path]
        else:
            norm_query = concept_id_or_path.replace("\\", "/").strip().lower()
            for cid, info in self._index_cache.items():
                if info["path"].lower() == norm_query or cid.lower() == norm_query:
                    target_info = info
                    break

        if not target_info:
            return f"Error: Concept '{concept_id_or_path}' not found in OKF bundle."

        content = target_info["abs_path"].read_text(encoding="utf-8")

        # Trust and freshness check (Timezone-safe UTC comparison)
        stale_msg = "FRESH"
        stale_after = target_info.get("stale_after")
        if stale_after:
            try:
                dt_str = str(stale_after).replace("Z", "+00:00")
                stale_dt = datetime.fromisoformat(dt_str)
                if stale_dt.tzinfo is None:
                    stale_dt = stale_dt.replace(tzinfo=timezone.utc)
                if stale_dt < datetime.now(timezone.utc):
                    stale_msg = f"EXPIRED / STALE (Expired on {stale_after})"
            except ValueError:
                pass

        header = (
            f"=== [OKF CONCEPT RETRIEVED] ===\n"
            f"Concept ID : {target_info['id']}\n"
            f"Title      : {target_info['title']}\n"
            f"Type       : {target_info['type']}\n"
            f"Verification: {target_info['verified']}\n"
            f"Freshness  : {stale_msg}\n"
            f"Source File: {target_info['path']}\n"
            f"================================\n\n"
        )
        return header + content

    def inspect_trust(self, concept_id: str) -> str:
        """Inspect the trust signals, verifier, and provenance of a concept."""
        info = self._index_cache.get(concept_id)
        if not info:
            for cid, i in self._index_cache.items():
                if concept_id.lower() in cid.lower():
                    info = i
                    break

        if not info:
            return f"Error: Concept '{concept_id}' not found."

        meta = info["metadata"]
        return (
            f"Trust Signals for `{info['id']}`:\n"
            f"- Status: {meta.get('status', 'unknown')}\n"
            f"- Verification: {info['verified']}\n"
            f"- Generated By: {meta.get('generated', 'None')}\n"
            f"- Freshness Boundary: {meta.get('stale_after', 'None')}\n"
            f"- Upstream Sources: {meta.get('sources', [])}\n"
            f"- Cross References: {meta.get('references', [])}\n"
        )

    def list_all_concepts(self) -> str:
        """List all concepts available in the OKF bundle."""
        rows = []
        for cid, info in self._index_cache.items():
            if info["path"] in ["index.md", "log.md"]:
                continue
            rows.append(
                f"- `{cid}`: {info['title']} (Type: {info['type']}, Status: {info['status']})"
            )
        return "Registered OKF Concepts:\n" + "\n".join(sorted(rows))
