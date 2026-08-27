import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Import loader and parser modules
from document_loader import DocumentLoader
from document_parser import DocumentElement, DocumentParser, ParsedDocument

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# =====================================================================
# DATA MODELS FOR NORMALIZED DOCUMENTS & UNITS
# =====================================================================

@dataclass
class NormalizedUnit:
    """Represents a normalized structural unit within a document.

    Explicitly handles sections, page numbers, slide numbers, sheet names,
    and table formats with rich unit-level metadata.
    """
    unit_id: str
    unit_type: str  # 'page', 'slide', 'sheet', 'section', 'table', 'document'
    unit_index: int  # 1-indexed sequence number
    title: str
    content: str
    page_number: Optional[int] = None
    slide_number: Optional[int] = None
    sheet_name: Optional[str] = None
    section_name: Optional[str] = None
    is_table: bool = False
    table_info: Optional[Dict[str, Any]] = None  # {rows, cols, headers}
    breadcrumbs: str = ""
    char_count: int = 0
    word_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert unit to dictionary representation."""
        return {
            "unit_id": self.unit_id,
            "unit_type": self.unit_type,
            "unit_index": self.unit_index,
            "title": self.title,
            "content": self.content,
            "page_number": self.page_number,
            "slide_number": self.slide_number,
            "sheet_name": self.sheet_name,
            "section_name": self.section_name,
            "is_table": self.is_table,
            "table_info": self.table_info,
            "breadcrumbs": self.breadcrumbs,
            "char_count": self.char_count,
            "word_count": self.word_count,
            "metadata": self.metadata,
        }


@dataclass
class NormalizedDocument:
    """Standardized container for a cleaned and structurally normalized document."""
    file_path: str
    file_name: str
    relative_path: str
    file_type: str
    category: str
    document_type: str
    content: str
    units: List[NormalizedUnit] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def total_units(self) -> int:
        return len(self.units)

    def to_dict(self) -> Dict[str, Any]:
        """Convert normalized document to dictionary format."""
        return {
            "file_path": self.file_path,
            "file_name": self.file_name,
            "relative_path": self.relative_path,
            "file_type": self.file_type,
            "category": self.category,
            "document_type": self.document_type,
            "content": self.content,
            "units": [unit.to_dict() for unit in self.units],
            "metadata": self.metadata,
            "error": self.error,
        }


# =====================================================================
# STEP 3: LOSS-LESS TEXT CLEANER
# =====================================================================

class TextCleaner:
    """Loss-less text cleaning module.

    Cleans noise, normalizes unicode, unifies line endings, and trims excessive
    whitespace while strictly preserving all text content, numbers, Markdown tables,
    code blocks, lists, and formatting.
    """

    @staticmethod
    def clean_text(text: str) -> str:
        """Cleans raw text with zero information loss."""
        if not text:
            return ""

        # 1. Normalize line endings (\r\n or \r -> \n)
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 2. Normalize unicode spaces (non-breaking space \xa0 -> standard space)
        text = text.replace("\xa0", " ").replace("\xad", "")

        # 3. Remove non-printable ASCII control chars (preserving \n, \t, \r)
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

        # 4. Trim trailing whitespace per line while preserving indentation
        lines = [line.rstrip() for line in text.split("\n")]
        text = "\n".join(lines)

        # 5. Limit runs of 3+ consecutive empty lines down to 2 empty lines
        text = re.sub(r"\n{4,}", "\n\n\n", text)

        return text.strip()


# =====================================================================
# STEP 4: STRUCTURAL NORMALIZER
# =====================================================================

class StructuralNormalizer:
    """Normalizes document units into a unified hierarchy.

    Standardizes pages, slides, sheets, sections, and table formats
    with explicit unit numbers, titles, and breadcrumbs.
    """

    def normalize(self, doc: ParsedDocument) -> NormalizedDocument:
        """Transforms a ParsedDocument into a NormalizedDocument with structured units."""
        rel_path = doc.metadata.get("relative_path", doc.file_name)
        cleaned_full_content = TextCleaner.clean_text(doc.content)

        normalized_units: List[NormalizedUnit] = []

        if doc.elements:
            for idx, el in enumerate(doc.elements, start=1):
                unit = self._normalize_element(el, idx, doc)
                if unit:
                    normalized_units.append(unit)
        else:
            # Create a single default unit if no structural elements existed
            words = len(cleaned_full_content.split())
            unit = NormalizedUnit(
                unit_id=f"{doc.file_name}_unit_1",
                unit_type="document",
                unit_index=1,
                title=Path(doc.file_name).stem,
                content=cleaned_full_content,
                breadcrumbs=f"{doc.category} > {doc.file_name}",
                char_count=len(cleaned_full_content),
                word_count=words,
            )
            normalized_units.append(unit)

        # Infer document classification type (policy, handbook, guide, spreadsheet, presentation, etc.)
        doc_type = self._infer_document_type(doc.file_name, doc.file_type, doc.category)

        return NormalizedDocument(
            file_path=doc.file_path,
            file_name=doc.file_name,
            relative_path=rel_path,
            file_type=doc.file_type,
            category=doc.category,
            document_type=doc_type,
            content=cleaned_full_content,
            units=normalized_units,
            error=doc.error,
        )

    def _normalize_element(
        self, el: DocumentElement, index: int, parent_doc: ParsedDocument
    ) -> Optional[NormalizedUnit]:
        """Normalizes an individual DocumentElement into a NormalizedUnit."""
        cleaned_content = TextCleaner.clean_text(el.content)
        if not cleaned_content:
            return None

        unit_type = el.element_type.lower()
        title = el.title or f"{unit_type.capitalize()} {index}"

        # Contextual metadata fields
        page_num = el.metadata.get("page_number")
        slide_num = index if unit_type == "slide" else None
        sheet_name = el.title if unit_type == "sheet" else None
        section_name = el.title if unit_type == "section" else None

        if unit_type == "page" and page_num is None:
            page_num = index

        # Table detection and metadata extraction
        is_table = (unit_type == "table") or ("|" in cleaned_content and "\n" in cleaned_content)
        table_info = None

        if is_table:
            table_info = self._extract_table_info(cleaned_content, el.metadata)

        # Construct breadcrumbs: Category > File Name > Unit Title
        breadcrumbs = f"{parent_doc.category} > {parent_doc.file_name} > {title}"

        words = len(cleaned_content.split())
        unit_id = f"{parent_doc.file_name}_{unit_type}_{index}"

        return NormalizedUnit(
            unit_id=unit_id,
            unit_type=unit_type,
            unit_index=index,
            title=title,
            content=cleaned_content,
            page_number=page_num,
            slide_number=slide_num,
            sheet_name=sheet_name,
            section_name=section_name,
            is_table=is_table,
            table_info=table_info,
            breadcrumbs=breadcrumbs,
            char_count=len(cleaned_content),
            word_count=words,
            metadata=dict(el.metadata),
        )

    def _extract_table_info(self, content: str, el_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts structural metadata for table formats (rows, columns, headers)."""
        rows = el_metadata.get("rows", 0)
        cols = el_metadata.get("columns", 0)

        # If not present in element metadata, attempt parsing Markdown table pipe structure
        if rows == 0 or cols == 0:
            lines = [line.strip() for line in content.split("\n") if line.strip().startswith("|")]
            if lines:
                rows = len(lines)
                cols = max(line.count("|") - 1 for line in lines) if lines else 0

        return {
            "rows": rows,
            "columns": cols,
            "has_markdown_format": "|" in content,
        }

    def _infer_document_type(self, file_name: str, file_type: str, category: str) -> str:
        """Infers high-level document classification (policy, handbook, guide, spreadsheet, presentation, etc.)."""
        fname_lower = file_name.lower()
        if "handbook" in fname_lower:
            return "handbook"
        elif "policy" in fname_lower or "rules" in fname_lower:
            return "policy"
        elif "guide" in fname_lower or "guidelines" in fname_lower or "standards" in fname_lower:
            return "guideline"
        elif "playbook" in fname_lower:
            return "playbook"
        elif "catalog" in fname_lower:
            return "catalog"
        elif file_type in (".xlsx", ".xls", ".csv"):
            return "spreadsheet"
        elif file_type in (".pptx", ".ppt"):
            return "presentation"
        elif file_type == ".pdf":
            return "pdf_document"
        else:
            return "text_document"


# =====================================================================
# STEP 5: METADATA ENRICHER
# =====================================================================

class MetadataEnricher:
    """Enriches documents and units with comprehensive document-level and unit-level metadata.

    (Note: Checksums/SHA hashes are excluded per user preference).
    """

    def enrich(self, doc: NormalizedDocument) -> NormalizedDocument:
        """Enriches document and unit level metadata."""
        total_chars = len(doc.content)
        total_words = len(doc.content.split())
        table_count = sum(1 for unit in doc.units if unit.is_table)
        est_reading_time = round(total_words / 200, 1)  # ~200 words per minute

        # Document-Level Metadata
        doc_metadata = {
            "file_name": doc.file_name,
            "relative_path": doc.relative_path,
            "category": doc.category,
            "file_type": doc.file_type,
            "document_type": doc.document_type,
            "total_units": doc.total_units,
            "total_words": total_words,
            "total_chars": total_chars,
            "table_count": table_count,
            "estimated_reading_time_minutes": est_reading_time,
            "has_tables": table_count > 0,
        }

        doc.metadata.update(doc_metadata)

        # Unit-Level Metadata Enrichment
        for unit in doc.units:
            unit.metadata.update({
                "parent_document": doc.file_name,
                "category": doc.category,
                "document_type": doc.document_type,
                "relative_path": doc.relative_path,
            })

        return doc


# =====================================================================
# PIPELINE ORCHESTRATOR & EXPORTER
# =====================================================================

class DocumentCleanerPipeline:
    """Complete Pipeline orchestrating Loading -> Parsing -> Cleaning -> Normalizing -> Metadata Enrichment."""

    def __init__(
        self,
        source_dir: Union[str, Path] = r"d:\RAG\Datasource",
        max_workers: int = 6,
    ):
        self.loader = DocumentLoader(source_dir=source_dir, max_workers=max_workers)
        self.normalizer = StructuralNormalizer()
        self.enricher = MetadataEnricher()

    def process_all(
        self, source_dir: Optional[Union[str, Path]] = None
    ) -> List[NormalizedDocument]:
        """Runs full cleaning, normalization, and metadata enrichment across dataset."""
        parsed_docs = self.loader.load_all(source_dir=source_dir, parallel=True)
        normalized_docs: List[NormalizedDocument] = []

        for parsed_doc in parsed_docs:
            normalized_doc = self.normalizer.normalize(parsed_doc)
            enriched_doc = self.enricher.enrich(normalized_doc)
            normalized_docs.append(enriched_doc)

        logger.info(f"Pipeline processed {len(normalized_docs)} normalized documents successfully.")
        return normalized_docs

    def export_normalized_outputs(
        self,
        output_dir: Union[str, Path] = r"d:\RAG\normalized_outputs",
        source_dir: Optional[Union[str, Path]] = None,
    ) -> List[Path]:
        """Runs pipeline and exports normalized outputs to text files and JSON summaries."""
        target_dir = Path(output_dir).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)

        norm_docs = self.process_all(source_dir=source_dir)
        exported_files: List[Path] = []

        for doc in norm_docs:
            rel_path = Path(doc.relative_path)
            out_file_name = f"{rel_path.stem}_normalized.txt"
            out_file_path = target_dir / rel_path.parent / out_file_name
            out_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Build readable normalized view with structural unit tags and table formatting
            lines = [
                "=" * 85,
                f"DOCUMENT        : {doc.file_name}",
                f"RELATIVE PATH   : {doc.relative_path}",
                f"CATEGORY        : {doc.category}",
                f"DOCUMENT TYPE   : {doc.document_type}",
                f"FILE TYPE       : {doc.file_type}",
                f"TOTAL UNITS     : {doc.total_units} unit(s)",
                f"TOTAL WORDS     : {doc.metadata.get('total_words'):,}",
                f"TOTAL CHARACTERS: {doc.metadata.get('total_chars'):,}",
                f"TABLE COUNT     : {doc.metadata.get('table_count')}",
                "=" * 85,
                "\n"
            ]

            lines.append("--- STRUCTURAL UNITS & BREADCRUMBS ---")
            for unit in doc.units:
                table_flag = "[TABLE FORMAT]" if unit.is_table else ""
                lines.append(f"• ID: {unit.unit_id}")
                lines.append(f"  Type: {unit.unit_type.upper()} | Title: {unit.title} {table_flag}")
                lines.append(f"  Breadcrumbs: {unit.breadcrumbs}")
                if unit.page_number:
                    lines.append(f"  Page: {unit.page_number}")
                if unit.slide_number:
                    lines.append(f"  Slide: {unit.slide_number}")
                if unit.sheet_name:
                    lines.append(f"  Sheet: {unit.sheet_name}")
                if unit.section_name:
                    lines.append(f"  Section: {unit.section_name}")
                if unit.table_info:
                    lines.append(f"  Table Info: {unit.table_info}")
                lines.append(f"  Length: {unit.char_count:,} chars ({unit.word_count} words)")
                lines.append("")

            lines.append("=" * 85)
            lines.append("--- NORMALIZED CONTENT ---\n")

            for unit in doc.units:
                lines.append(f"=== [{unit.unit_type.upper()} {unit.unit_index}: {unit.title}] ===")
                lines.append(f"Breadcrumbs: {unit.breadcrumbs}")
                lines.append(unit.content)
                lines.append("")

            with open(out_file_path, "w", encoding="utf-8", errors="replace") as f:
                f.write("\n".join(lines))

            exported_files.append(out_file_path)

        # Save JSON summary of normalized dataset
        summary_path = target_dir / "normalized_dataset_summary.json"
        summary_data = {
            "total_documents": len(norm_docs),
            "total_structural_units": sum(d.total_units for d in norm_docs),
            "total_characters": sum(d.metadata.get("total_chars", 0) for d in norm_docs),
            "total_words": sum(d.metadata.get("total_words", 0) for d in norm_docs),
            "total_tables": sum(d.metadata.get("table_count", 0) for d in norm_docs),
            "documents": [d.to_dict() for d in norm_docs],
        }

        with open(summary_path, "w", encoding="utf-8", errors="replace") as f:
            json.dump(summary_data, f, indent=2)

        logger.info(f"Exported {len(exported_files)} normalized text files and dataset summary to {target_dir}")
        return exported_files


if __name__ == "__main__":
    print("=" * 70)
    print("  RAG PIPELINE: CLEANING, NORMALIZATION & METADATA ENRICHMENT DEMO  ")
    print("=" * 70)

    pipeline = DocumentCleanerPipeline(source_dir=r"d:\RAG\Datasource", max_workers=6)
    out_files = pipeline.export_normalized_outputs(output_dir=r"d:\RAG\normalized_outputs")

    print(f"\n[PIPELINE COMPLETE] Successfully cleaned, normalized & enriched {len(out_files)} files!")
    print(f"Normalized Outputs saved in: d:\\RAG\\normalized_outputs")
