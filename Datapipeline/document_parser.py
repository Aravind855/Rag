"""Document Parser Module (Functional Approach).

Provides pure, standalone functions to parse PDF, DOCX, PPTX, XLSX, JSON,
Markdown, and Plain Text files into structure-aware Markdown representations,
returning LangChain Document objects.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# LangChain Document representation
from langchain_core.documents import Document

# Third-party parsing libraries
import docx
from docx.table import Table
from docx.text.paragraph import Paragraph
import openpyxl
import pandas as pd
from pptx import Presentation
import pymupdf4llm

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("document_parser")

# verified
def clean_stem_name(stem: str) -> str:
    """Cleans file stem by stripping duplicate download markers like (1), _1,

    and trailing whitespace.
    """
    cleaned = re.sub(r"\s*\(\d+\)\s*", "", stem)
    cleaned = re.sub(r"_\d+$", "", cleaned)
    return cleaned.strip()

# verified
def parse_pdf(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Parses PDF into Markdown using pymupdf4llm, extracting tables as GFM

    Markdown and preserving page markers.
    """
    path = Path(file_path).resolve()
    try:
        pages_data = pymupdf4llm.to_markdown(str(path), page_chunks=True)
        full_parts: List[str] = []
        total_tables = 0

        for idx, page in enumerate(pages_data, start=1):
            p_text = page.get("text", "").strip()
            if not p_text:
                continue
            # Count table rows
            total_tables += p_text.count("| --- |") + p_text.count("|---|")
            full_parts.append(f"<!-- Page {idx} -->\n{p_text}")

        full_md = "\n\n".join(full_parts)
        return {
            "content": full_md,
            "total_pages": len(pages_data),
            "table_count": max(total_tables, 1 if "|---|" in full_md or "| --- |" in full_md else 0),
        }
    except Exception as e:
        logger.warning(f"pymupdf4llm failed on {path.name}: {e}. Falling back to basic fitz...")
        import pymupdf as fitz
        doc = fitz.open(str(path))
        pages = [f"<!-- Page {i + 1} -->\n" + doc[i].get_text() for i in range(len(doc))]
        doc.close()
        return {"content": "\n\n".join(pages), "total_pages": len(pages), "table_count": 0}


# verified
def parse_docx(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Parses DOCX document sequentially, converting paragraphs, headings, and

    tables to GitHub-Flavored Markdown.
    """
    path = Path(file_path).resolve()
    doc = docx.Document(str(path))
    md_elements: List[str] = []
    table_count = 0

    for child in doc.element.body:
        if child.tag.endswith("p"):
            p = Paragraph(child, doc)
            text = p.text.strip()
            if not text:
                continue
            style_name = p.style.name.lower() if p.style else ""
            if "heading 1" in style_name:
                md_elements.append(f"\n# {text}\n")
            elif "heading 2" in style_name:
                md_elements.append(f"\n## {text}\n")
            elif "heading 3" in style_name:
                md_elements.append(f"\n### {text}\n")
            elif "heading" in style_name:
                md_elements.append(f"\n#### {text}\n")
            elif "list bullet" in style_name or style_name.startswith("bullet"):
                md_elements.append(f"- {text}")
            elif "list number" in style_name:
                md_elements.append(f"1. {text}")
            else:
                md_elements.append(text)

        elif child.tag.endswith("tbl"):
            table = Table(child, doc)
            rows_data: List[List[str]] = []
            for row in table.rows:
                cells = [cell.text.strip().replace("\n", " ").replace("|", "\\|") for cell in row.cells]
                rows_data.append(cells)

            if rows_data:
                table_count += 1
                header = rows_data[0]
                header_line = "| " + " | ".join(header) + " |"
                separator_line = "| " + " | ".join([":---"] * len(header)) + " |"
                body_lines = []
                for row in rows_data[1:]:
                    if len(row) < len(header):
                        row.extend([""] * (len(header) - len(row)))
                    elif len(row) > len(header):
                        row = row[: len(header)]
                    body_lines.append("| " + " | ".join(row) + " |")

                md_table = "\n".join([header_line, separator_line] + body_lines)
                md_elements.append(f"\n{md_table}\n")

    return {
        "content": "\n\n".join(md_elements),
        "table_count": table_count,
        "paragraph_count": len(doc.paragraphs),
    }

# verified
def parse_pptx(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Parses PPTX presentation slide-by-slide preserving title hierarchy, bullet

    indentation, tables, and presenter notes.
    """
    path = Path(file_path).resolve()
    prs = Presentation(str(path))
    slide_parts: List[str] = []
    table_count = 0

    for idx, slide in enumerate(prs.slides, start=1):
        slide_title = f"Slide {idx}"
        if slide.shapes.title and slide.shapes.title.text:
            slide_title = slide.shapes.title.text.strip().replace("\n", " ")

        slide_md: List[str] = [f"## Slide {idx}: {slide_title}\n"]

        for shape in slide.shapes:
            if shape.has_text_frame:
                for p in shape.text_frame.paragraphs:
                    text = p.text.strip()
                    if not text or text == slide_title:
                        continue
                    indent = "  " * (p.level if hasattr(p, "level") and p.level else 0)
                    slide_md.append(f"{indent}- {text}")

            elif shape.has_table:
                table_count += 1
                rows_data = []
                for r in shape.table.rows:
                    row_cells = [cell.text.strip().replace("\n", " ").replace("|", "\\|") for cell in r.cells]
                    rows_data.append(row_cells)
                if rows_data:
                    header = rows_data[0]
                    header_line = "| " + " | ".join(header) + " |"
                    separator_line = "| " + " | ".join([":---"] * len(header)) + " |"
                    body_lines = ["| " + " | ".join(r) + " |" for r in rows_data[1:]]
                    slide_md.append("\n" + "\n".join([header_line, separator_line] + body_lines) + "\n")

        if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                slide_md.append(f"\n> **Presenter Notes:** {notes}\n")

        slide_parts.append("\n".join(slide_md))

    return {
        "content": "\n\n---\n\n".join(slide_parts),
        "slide_count": len(prs.slides),
        "table_count": table_count,
    }

# verified
def parse_excel(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Parses Excel workbooks (.xlsx, .xls) sheet-by-sheet into GitHub-Flavored

    Markdown tables.
    """
    path = Path(file_path).resolve()
    excel_file = pd.ExcelFile(str(path), engine="openpyxl")
    sheet_parts: List[str] = []
    total_records = 0

    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        df = df.dropna(how="all")
        if df.empty:
            continue

        total_records += len(df)
        sheet_md = [f"### Sheet: {sheet_name}\n"]
        sheet_md.append(f"*Total Records: {len(df)} | Columns: {len(df.columns)}*\n")
        try:
            table_str = df.to_markdown(index=False)
        except Exception:
            table_str = df.to_string(index=False)
        sheet_md.append(table_str)
        sheet_parts.append("\n".join(sheet_md))

    return {
        "content": "\n\n---\n\n".join(sheet_parts),
        "total_sheets": len(excel_file.sheet_names),
        "total_records": total_records,
        "table_count": len(sheet_parts),
    }

# verified
def parse_json(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Parses JSON documents dynamically, converting structured catalogs

    (like system_catalog.json) into human-readable Markdown tables and profiles.
    """
    path = Path(file_path).resolve()
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)

    # Check if this is the system catalog format
    if isinstance(data, dict) and ("systems" in data or "catalog_metadata" in data):
        md_parts: List[str] = []
        meta = data.get("catalog_metadata", {})
        md_parts.append(f"# {meta.get('catalog_id', 'System Catalog')} - System Inventory\n")
        md_parts.append(f"> **Version:** {meta.get('version')} | **Effective Date:** {meta.get('effective_date')} | **Review:** {meta.get('last_review')}")
        md_parts.append(f"> **Owner:** {meta.get('owner')} | **Classification:** {meta.get('classification')}")
        md_parts.append(f"> **Description:** {meta.get('description', '')}\n")

        envs = data.get("environment_definitions", {})
        if envs:
            md_parts.append("## Environment Definitions\n")
            md_parts.append("| Environment | Definition / Purpose |")
            md_parts.append("| :--- | :--- |")
            for env_name, env_desc in envs.items():
                md_parts.append(f"| {env_name} | {env_desc} |")
            md_parts.append("")

        systems = data.get("systems", [])
        if systems:
            md_parts.append("## Systems Summary Matrix\n")
            headers = ["System ID", "Name", "Category", "Criticality", "Environment", "Availability", "RTO (min)", "RPO (min)", "Primary Region", "Dependencies"]
            md_parts.append("| " + " | ".join(headers) + " |")
            md_parts.append("| " + " | ".join([":---"] * len(headers)) + " |")
            for s in systems:
                deps = ", ".join(s.get("dependencies", [])) or "None"
                row = [
                    s.get("system_id", ""),
                    s.get("name", "").replace("|", "\\|"),
                    s.get("category", ""),
                    s.get("criticality", ""),
                    s.get("environment", ""),
                    s.get("availability_target", ""),
                    str(s.get("rto_minutes", "")),
                    str(s.get("rpo_minutes", "")),
                    s.get("primary_region", ""),
                    deps,
                ]
                md_parts.append("| " + " | ".join(row) + " |")
            md_parts.append("")

            md_parts.append("## Detailed System Profiles\n")
            for s in systems:
                md_parts.append(f"### {s.get('system_id')}: {s.get('name')}\n")
                md_parts.append(f"- **Category:** {s.get('category')}")
                md_parts.append(f"- **Criticality:** {s.get('criticality')}")
                md_parts.append(f"- **Owner Team:** {s.get('owner_team')}")
                md_parts.append(f"- **Business Owner:** {s.get('business_owner')}")
                md_parts.append(f"- **Environment:** {s.get('environment')}")
                md_parts.append(f"- **Data Classification:** {s.get('data_classification')}")
                md_parts.append(f"- **Availability Target:** {s.get('availability_target')}")
                md_parts.append(f"- **RTO:** {s.get('rto_minutes')} min | **RPO:** {s.get('rpo_minutes')} min")
                md_parts.append(f"- **Primary Region:** {s.get('primary_region')} | **Recovery Region:** {s.get('recovery_region')}")
                md_parts.append(f"- **Authentication:** {s.get('authentication')}")
                deps = ", ".join(s.get("dependencies", [])) or "None"
                md_parts.append(f"- **Dependencies:** {deps}")
                md_parts.append(f"- **Vendor:** {s.get('vendor')}")
                md_parts.append(f"- **Last Review:** {s.get('last_review')}\n")

        return {
            "content": "\n".join(md_parts),
            "table_count": 2,
            "total_systems": len(systems),
        }

    # Generic JSON formatting
    formatted = json.dumps(data, indent=2)
    return {"content": f"```json\n{formatted}\n```", "table_count": 0}

# verified
def parse_text(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Parses Markdown, Text, or configuration files across multiple encodings."""
    path = Path(file_path).resolve()
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    content = ""
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                content = f.read()
            break
        except Exception:
            continue

    if not content:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

    table_count = content.count("| --- |") + content.count("|---|")
    return {"content": content, "table_count": table_count}

# verified
def parse_document(file_path: Union[str, Path], category: str = "general") -> Document:
    """Dispatches parsing to the appropriate function by file extension and

    returns a LangChain Document.
    """
    path = Path(file_path).resolve()
    ext = path.suffix.lower()
    clean_stem = clean_stem_name(path.stem)

    if ext == ".pdf":
        result = parse_pdf(path)
    elif ext in (".docx", ".doc"):
        result = parse_docx(path)
    elif ext in (".pptx", ".ppt"):
        result = parse_pptx(path)
    elif ext in (".xlsx", ".xls"):
        result = parse_excel(path)
    elif ext in (".json", ".jsonl"):
        result = parse_json(path)
    else:
        result = parse_text(path)

    content = result.get("content", "")
    table_count = result.get("table_count", 0)

    metadata: Dict[str, Any] = {
        "file_name": path.name,
        "clean_name": f"{clean_stem}.md",
        "category": category,
        "file_type": ext,
        "file_size_bytes": path.stat().st_size if path.exists() else 0,
        "has_tables": table_count > 0,
        "table_count": table_count,
        "breadcrumbs": f"{category} > {path.name}",
    }

    # Add extra metadata extracted by parsers
    for k, v in result.items():
        if k not in ("content", "table_count"):
            metadata[k] = v

    return Document(page_content=content, metadata=metadata)
