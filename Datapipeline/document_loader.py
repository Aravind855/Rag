import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from document_parser import DocumentParser, ParsedDocument

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DocumentLoader:
    """Dynamic, scalable DocumentLoader.

    Discovers and parses ANY file structure, depth, and format from a given dataset
    without hardcoded extension restrictions or fixed directory assumptions.
    """

    def __init__(
        self,
        source_dir: Union[str, Path] = r"d:\RAG\Datasource",
        parser: Optional[DocumentParser] = None,
        max_workers: int = 4,
    ):
        self.source_dir = Path(source_dir).resolve()
        self.parser = parser or DocumentParser()
        self.max_workers = max_workers

    def discover_files(self, source_dir: Optional[Union[str, Path]] = None) -> List[Tuple[Path, Dict[str, Any]]]:
        """Recursively scans the target directory to discover ALL processable files dynamically.

        Args:
            source_dir: Directory path to scan (defaults to self.source_dir).

        Returns:
            List of tuples (file_path, metadata_dict).
        """
        root_dir = Path(source_dir).resolve() if source_dir else self.source_dir

        if not root_dir.exists():
            logger.error(f"Source directory does not exist: {root_dir}")
            return []

        discovered: List[Tuple[Path, Dict[str, Any]]] = []

        for item in root_dir.rglob("*"):
            # Skip directories, system files, and lock files (e.g. ~$lock files)
            if not item.is_file():
                continue
            if item.name.startswith(".") or item.name.startswith("~$"):
                continue

            # Dynamically determine path metadata and directory hierarchy
            try:
                rel_path = item.relative_to(root_dir)
                parts = rel_path.parts
                subfolders = list(parts[:-1]) if len(parts) > 1 else []
                category = "/".join(subfolders) if subfolders else "root"
            except ValueError:
                subfolders = []
                category = "general"

            file_info = {
                "category": category,
                "relative_path": str(rel_path) if 'rel_path' in locals() else item.name,
                "subfolders": subfolders,
                "file_size_bytes": item.stat().st_size if item.exists() else 0,
                "extension": item.suffix.lower() or "no_extension",
            }

            discovered.append((item, file_info))

        logger.info(f"Discovered {len(discovered)} files dynamically in {root_dir}")
        return discovered

    def load_single(self, file_path: Union[str, Path], file_info: Optional[Dict[str, Any]] = None) -> ParsedDocument:
        """Loads and parses a single document file, enriching it with dynamic path metadata.

        Args:
            file_path: Path to the document.
            file_info: Metadata dictionary containing path/category details.

        Returns:
            ParsedDocument object.
        """
        path = Path(file_path).resolve()
        info = file_info or {"category": "general", "relative_path": path.name, "subfolders": []}
        category = info.get("category", "general")

        doc = self.parser.parse(path, category=category)

        # Enrich ParsedDocument metadata with dynamic path & file details
        doc.metadata.update({
            "relative_path": info.get("relative_path", path.name),
            "subfolders": info.get("subfolders", []),
            "file_size_bytes": info.get("file_size_bytes", 0),
        })

        return doc

    def load_all(
        self,
        source_dir: Optional[Union[str, Path]] = None,
        parallel: bool = True,
    ) -> List[ParsedDocument]:
        """Loads and parses all discovered documents dynamically.

        Args:
            source_dir: Directory path to scan.
            parallel: Whether to use multithreading for concurrent file loading.

        Returns:
            List of ParsedDocument objects.
        """
        files_to_process = self.discover_files(source_dir)

        if not files_to_process:
            logger.warning("No files found to load.")
            return []

        results: List[ParsedDocument] = []
        start_time = time.time()

        if parallel and len(files_to_process) > 1:
            logger.info(f"Loading {len(files_to_process)} documents dynamically using {self.max_workers} threads...")
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_file = {
                    executor.submit(self.load_single, file_path, file_info): (file_path, file_info)
                    for file_path, file_info in files_to_process
                }

                for future in as_completed(future_to_file):
                    file_path, file_info = future_to_file[future]
                    try:
                        doc = future.result()
                        results.append(doc)
                    except Exception as e:
                        logger.error(f"Unhandled exception loading {file_path.name}: {str(e)}")
                        results.append(
                            ParsedDocument(
                                file_path=str(file_path),
                                file_name=file_path.name,
                                file_type=file_path.suffix.lower(),
                                category=file_info.get("category", "general"),
                                content="",
                                error=f"Unhandled exception: {str(e)}",
                            )
                        )
        else:
            logger.info(f"Loading {len(files_to_process)} documents sequentially...")
            for file_path, file_info in files_to_process:
                doc = self.load_single(file_path, file_info)
                results.append(doc)

        elapsed = time.time() - start_time
        logger.info(f"Successfully processed {len(results)} documents in {elapsed:.2f} seconds.")
        return results

    def load_as_dict(
        self,
        source_dir: Optional[Union[str, Path]] = None,
        parallel: bool = True,
    ) -> List[Dict[str, Any]]:
        """Loads all documents and returns them as a list of dictionaries."""
        docs = self.load_all(source_dir=source_dir, parallel=parallel)
        return [doc.to_dict() for doc in docs]

    def get_summary_stats(self, documents: List[ParsedDocument]) -> Dict[str, Any]:
        """Calculates dataset summary metrics for loaded documents."""
        total_docs = len(documents)
        total_chars = sum(len(doc.content) for doc in documents)
        total_elements = sum(len(doc.elements) for doc in documents)
        error_count = sum(1 for doc in documents if doc.error is not None)

        category_counts: Dict[str, int] = {}
        format_counts: Dict[str, int] = {}

        for doc in documents:
            category_counts[doc.category] = category_counts.get(doc.category, 0) + 1
            format_counts[doc.file_type] = format_counts.get(doc.file_type, 0) + 1

        return {
            "total_documents": total_docs,
            "total_structural_elements": total_elements,
            "total_characters": total_chars,
            "error_count": error_count,
            "categories": category_counts,
            "file_formats": format_counts,
        }

    def export_to_folder(
        self,
        output_dir: Union[str, Path] = r"d:\RAG\output_test",
        source_dir: Optional[Union[str, Path]] = None,
        export_json: bool = True,
    ) -> List[Path]:
        """Parses all documents and exports extracted content into an output directory,
        preserving the exact subfolder structure of the source directory as text (.txt) files.

        Args:
            output_dir: Destination directory path for extracted text files.
            source_dir: Target source directory to load documents from.
            export_json: Whether to also save a JSON summary of the dataset.

        Returns:
            List of generated output file paths.
        """
        import json
        target_output = Path(output_dir).resolve()
        target_output.mkdir(parents=True, exist_ok=True)

        docs = self.load_all(source_dir=source_dir, parallel=True)
        exported_paths: List[Path] = []

        for doc in docs:
            rel_path_str = doc.metadata.get("relative_path", doc.file_name)
            rel_path = Path(rel_path_str)

            # Change extension to .txt for the exported file
            output_file_name = f"{rel_path.stem}_parsed.txt"
            output_file_path = target_output / rel_path.parent / output_file_name
            output_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Build formatted text content with metadata header
            header_lines = [
                "=" * 80,
                f"DOCUMENT TITLE: {doc.file_name}",
                f"CATEGORY      : {doc.category}",
                f"FILE FORMAT   : {doc.file_type}",
                f"ORIGINAL PATH : {doc.file_path}",
                f"RELATIVE PATH : {rel_path_str}",
                f"TOTAL UNITS   : {len(doc.elements)} structural unit(s)",
                f"CHAR COUNT    : {len(doc.content):,} characters",
                "=" * 80,
                "\n"
            ]

            # Structural breakdown section
            structural_lines = []
            if doc.elements:
                structural_lines.append("--- STRUCTURAL BREAKDOWN ---")
                for el in doc.elements:
                    title_str = f": {el.title}" if el.title else ""
                    structural_lines.append(f"[{el.element_type.upper()} {el.index}{title_str}] ({len(el.content)} chars)")
                structural_lines.append("\n" + "=" * 80 + "\n")

            full_export_text = "\n".join(header_lines) + "\n".join(structural_lines) + "--- EXTRACTED CONTENT ---\n\n" + doc.content

            with open(output_file_path, "w", encoding="utf-8", errors="replace") as f:
                f.write(full_export_text)

            exported_paths.append(output_file_path)

        if export_json:
            summary_path = target_output / "dataset_summary.json"
            summary_data = {
                "stats": self.get_summary_stats(docs),
                "documents": [doc.to_dict() for doc in docs]
            }
            with open(summary_path, "w", encoding="utf-8", errors="replace") as f:
                json.dump(summary_data, f, indent=2)

        logger.info(f"Exported {len(exported_paths)} parsed text files to {target_output}")
        return exported_paths


if __name__ == "__main__":
    print("=" * 65)
    print("        DYNAMIC RAG DOCUMENT LOADER & PARSER DEMO          ")
    print("=" * 65)

    loader = DocumentLoader(source_dir=r"d:\RAG\Datasource", max_workers=6)
    loaded_docs = loader.load_all(parallel=True)

    stats = loader.get_summary_stats(loaded_docs)

    print("\n--- Summary Statistics ---")
    print(f"Total Documents Loaded  : {stats['total_documents']}")
    print(f"Total Structural Units  : {stats['total_structural_elements']}")
    print(f"Total Character Count   : {stats['total_characters']:,}")
    print(f"Errors / Failures       : {stats['error_count']}")

    print("\nDynamic Category Breakdown:")
    for cat, count in stats["categories"].items():
        print(f"  - {cat:<20}: {count} files")

    print("\nFile Format Breakdown:")
    for fmt, count in stats["file_formats"].items():
        print(f"  - {fmt:<20}: {count} files")

    # Export parsed output text files for inspection & testing
    output_directory = Path(r"d:\RAG\parsed_outputs")
    exported_files = loader.export_to_folder(output_dir=output_directory)
    print(f"\n[EXPORT COMPLETE] Exported {len(exported_files)} text files to: {output_directory}")
