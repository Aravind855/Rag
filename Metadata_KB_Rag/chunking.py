"""
Chunking Engine for NexaCore Knowledge Base RAG (Project 2).

Provides two distinct chunking strategies:
1. StructureAwareChunker (Structure-Aware + Sentence-Aware Chunking):
   - Uses MarkdownNodeParser (#, ##, ###) for hard structural boundaries.
   - Uses SentenceSplitter for sentence-boundary sub-splitting.
   - Extracts section titles and header_path metadata.

2. SemanticChunker (True Semantic Boundary Chunking):
   - Uses LlamaIndex SemanticSplitterNodeParser with GeminiEmbedding (models/gemini-embedding-001).
   - Computes cosine similarity between consecutive sentence embeddings to detect topic shifts.
"""

import logging
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from llama_index.core import Document
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import MarkdownNodeParser, SemanticSplitterNodeParser, SentenceSplitter
from llama_index.core.schema import BaseNode, TextNode
from llama_index.embeddings.google import GeminiEmbedding

from metadata import configure_llamaindex_metadata_exclusions

logger = logging.getLogger(__name__)

# Pattern to extract clean heading text from Markdown line
HEADING_REGEX = re.compile(r"^(#{1,6})\s+(\*\*|\*|)(.*?)\2\s*$", re.MULTILINE)


class StructureAwareChunker:
    """Structure-Aware + Sentence-Aware Node Parser using LlamaIndex IngestionPipeline."""

    def __init__(
        self,
        max_chunk_size: int = 512,
        chunk_overlap: int = 50,
    ):
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

        # Initialize LlamaIndex IngestionPipeline with MarkdownNodeParser and SentenceSplitter
        self.pipeline = IngestionPipeline(
            transformations=[
                MarkdownNodeParser(),
                SentenceSplitter(chunk_size=max_chunk_size, chunk_overlap=chunk_overlap),
            ]
        )
        logger.info(
            f"Initialized StructureAwareChunker (Structure + Sentence-aware) "
            f"[chunk_size={max_chunk_size}, chunk_overlap={chunk_overlap}]"
        )

    @staticmethod
    def _clean_header_path(raw_path: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Extract clean section title and header_path string from raw LlamaIndex header_path."""
        if not raw_path or raw_path.strip() in ("/", ""):
            return None, None

        parts = [p.strip().strip("*").strip() for p in raw_path.split("/") if p.strip()]
        if not parts:
            return None, None

        section = parts[-1]
        header_path = " > ".join(parts)
        return section, header_path

    @staticmethod
    def _extract_heading_from_text(text: str) -> Optional[str]:
        """Extract the first heading text from a node's text content."""
        match = HEADING_REGEX.search(text)
        if match:
            return match.group(3).strip()
        return None

    def post_process_node(self, node: BaseNode, chunk_index: int) -> TextNode:
        """Enrich a transformed LlamaIndex node with section, header_path, and chunk IDs."""
        text = node.text.strip() if hasattr(node, "text") else ""
        raw_header_path = node.metadata.get("header_path")

        section, header_path = self._clean_header_path(raw_header_path)
        if not section:
            section = self._extract_heading_from_text(text)

        if section:
            node.metadata["section"] = section
        if header_path:
            node.metadata["header_path"] = header_path

        # Determine parent document ID
        parent_doc_id = node.metadata.get("doc_id", node.metadata.get("parent_doc_id", str(uuid.uuid4())))
        chunk_id = f"{parent_doc_id}_chunk_{chunk_index:03d}"
        valid_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))

        node.metadata["chunk_id"] = chunk_id
        node.metadata["chunk_index"] = chunk_index
        node.metadata["parent_doc_id"] = parent_doc_id
        node.metadata["chunk_type"] = "structure_sentence_aware"

        text_node = TextNode(
            text=text,
            metadata=dict(node.metadata),
            id_=valid_uuid,
        )

        text_node = configure_llamaindex_metadata_exclusions(text_node)
        return text_node

    def parse_all_documents(self, documents: List[Document]) -> List[TextNode]:
        """Run Structure + Sentence-Aware Chunking across all Documents."""
        if not documents:
            logger.warning("No documents provided to StructureAwareChunker. Returning empty list.")
            return []

        transformed_nodes = self.pipeline.run(documents=documents)

        final_nodes: List[TextNode] = []
        for i, node in enumerate(transformed_nodes):
            if hasattr(node, "text") and node.text.strip():
                enriched_node = self.post_process_node(node, chunk_index=i)
                final_nodes.append(enriched_node)

        logger.info(
            f"Structure-Aware + Sentence-Aware Chunking Complete: Generated {len(final_nodes)} "
            f"TextNode(s) across {len(documents)} document(s)."
        )
        return final_nodes


class RateLimitedGeminiEmbedding(GeminiEmbedding):
    """Wrapper around GeminiEmbedding that adds rate limit retry backoff for 429 errors."""

    def get_text_embedding_batch(
        self,
        texts: List[str],
        show_progress: bool = False,
        **kwargs: Any,
    ) -> List[List[float]]:
        results = []
        # Process in smaller sub-batches to respect free tier limits
        batch_size = 20
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            for attempt in range(5):
                try:
                    batch_embeddings = super()._get_text_embeddings(batch)
                    results.extend(batch_embeddings)
                    time.sleep(0.5)  # Pace requests to prevent hitting 100 req/min quota
                    break
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "Quota exceeded" in str(e):
                        wait_seconds = 15 * (attempt + 1)
                        logger.warning(f"Rate limit hit (429). Retrying in {wait_seconds}s (Attempt {attempt + 1}/5)...")
                        time.sleep(wait_seconds)
                    else:
                        raise e
        return results


class SemanticChunker:
    """True Semantic Chunker utilizing LlamaIndex SemanticSplitterNodeParser and sentence embeddings."""

    def __init__(
        self,
        embed_model: Optional[Any] = None,
        buffer_size: int = 1,
        breakpoint_percentile_threshold: int = 90,
    ):
        if embed_model is None:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable is required for SemanticChunker.")

            os.environ["GEMINI_API_KEY"] = api_key
            os.environ["GOOGLE_API_KEY"] = api_key

            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
            except Exception:
                pass

            embed_model = RateLimitedGeminiEmbedding(model_name="models/gemini-embedding-001", api_key=api_key)

        self.embed_model = embed_model
        self.semantic_splitter = SemanticSplitterNodeParser(
            buffer_size=buffer_size,
            breakpoint_percentile_threshold=breakpoint_percentile_threshold,
            embed_model=embed_model,
        )
        logger.info(
            f"Initialized SemanticChunker (buffer_size={buffer_size}, "
            f"percentile_threshold={breakpoint_percentile_threshold})"
        )

    def parse_all_documents(self, documents: List[Document]) -> List[TextNode]:
        """Run embedding-based semantic boundary detection across all Documents."""
        if not documents:
            logger.warning("No documents provided to SemanticChunker. Returning empty list.")
            return []

        semantic_nodes = self.semantic_splitter.get_nodes_from_documents(documents)

        final_nodes: List[TextNode] = []
        for i, node in enumerate(semantic_nodes):
            text = node.text.strip() if hasattr(node, "text") else ""
            if not text:
                continue

            parent_doc_id = node.metadata.get("doc_id", str(uuid.uuid4()))
            chunk_id = f"{parent_doc_id}_semantic_{i:03d}"
            valid_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))

            node.metadata["chunk_id"] = chunk_id
            node.metadata["chunk_index"] = i
            node.metadata["parent_doc_id"] = parent_doc_id
            node.metadata["chunk_type"] = "true_semantic"

            text_node = TextNode(
                text=text,
                metadata=dict(node.metadata),
                id_=valid_uuid,
            )

            text_node = configure_llamaindex_metadata_exclusions(text_node)
            final_nodes.append(text_node)

        logger.info(
            f"True Semantic Chunking Complete: Generated {len(final_nodes)} "
            f"semantic TextNode(s) across {len(documents)} document(s)."
        )
        return final_nodes


class HybridChunker:
    """Unified 2-Stage Hybrid Chunker combining Structure-Aware Section Parsing and Embedding Semantic Sub-Chunking.

    Stage 1: MarkdownNodeParser splits documents into structural sections and extracts header_path/section metadata.
    Stage 2: SemanticSplitterNodeParser (or SentenceSplitter) semantically sub-splits long sections based on embedding dissimilarity.
    """

    def __init__(
        self,
        embed_model: Optional[Any] = None,
        max_chunk_size: int = 512,
        chunk_overlap: int = 50,
        breakpoint_percentile_threshold: int = 90,
    ):
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

        if embed_model is None:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if api_key:
                os.environ["GEMINI_API_KEY"] = api_key
                os.environ["GOOGLE_API_KEY"] = api_key
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                except Exception:
                    pass
                embed_model = RateLimitedGeminiEmbedding(model_name="models/gemini-embedding-001", api_key=api_key)

        self.embed_model = embed_model
        self.markdown_parser = MarkdownNodeParser()

        if embed_model is not None:
            self.sub_splitter = SemanticSplitterNodeParser(
                buffer_size=1,
                breakpoint_percentile_threshold=breakpoint_percentile_threshold,
                embed_model=embed_model,
            )
        else:
            self.sub_splitter = SentenceSplitter(chunk_size=max_chunk_size, chunk_overlap=chunk_overlap)

        logger.info(
            f"Initialized HybridChunker [Structure-Aware + Semantic Sub-Chunking] "
            f"(embed_model={'Gemini' if embed_model else 'SentenceSplitter'})"
        )

    def parse_all_documents(self, documents: List[Document]) -> List[TextNode]:
        """Run 2-Stage Hybrid Chunking (Structure-Aware + Semantic Sub-Chunking)."""
        if not documents:
            logger.warning("No documents provided to HybridChunker. Returning empty list.")
            return []

        # Stage 1: Structure-Aware Markdown Section Splitting
        structural_nodes = self.markdown_parser.get_nodes_from_documents(documents)

        # Stage 2: Semantic (or Sentence-aware) Sub-Splitting within each structural section
        raw_final_nodes = self.sub_splitter.get_nodes_from_documents(structural_nodes)

        final_nodes: List[TextNode] = []
        for i, node in enumerate(raw_final_nodes):
            text = node.text.strip() if hasattr(node, "text") else ""
            if not text:
                continue

            raw_header_path = node.metadata.get("header_path")
            section, header_path = StructureAwareChunker._clean_header_path(raw_header_path)
            if not section:
                section = StructureAwareChunker._extract_heading_from_text(text)

            if section:
                node.metadata["section"] = section
            if header_path:
                node.metadata["header_path"] = header_path

            parent_doc_id = node.metadata.get("doc_id", str(uuid.uuid4()))
            chunk_id = f"{parent_doc_id}_hybrid_{i:03d}"
            valid_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))

            node.metadata["chunk_id"] = chunk_id
            node.metadata["chunk_index"] = i
            node.metadata["parent_doc_id"] = parent_doc_id
            node.metadata["chunk_type"] = "hybrid_structure_semantic"

            text_node = TextNode(
                text=text,
                metadata=dict(node.metadata),
                id_=valid_uuid,
            )

            text_node = configure_llamaindex_metadata_exclusions(text_node)
            final_nodes.append(text_node)

        logger.info(
            f"Hybrid Chunking Complete: Generated {len(final_nodes)} hybrid TextNode(s) "
            f"across {len(documents)} document(s)."
        )
        return final_nodes


def save_chunked_nodes(
    nodes: List[TextNode],
    output_dir: Optional[str] = None,
) -> Path:
    """Save all generated chunk nodes into JSON and formatted text files in output_dir.

    Args:
        nodes: List of LlamaIndex TextNode objects.
        output_dir: Target directory path (defaults to 'd:\\RAG\\Metadata_KB_Rag\\chunked_nodes').

    Returns:
        Path to the output directory.
    """
    import json
    if output_dir is None:
        target_dir = Path(__file__).resolve().parent / "chunked_nodes"
    else:
        target_dir = Path(output_dir)

    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Export complete JSON array of all chunk nodes
    serialized_nodes = []
    for node in nodes:
        node_dict = {
            "node_id": node.node_id,
            "text": node.text,
            "metadata": node.metadata,
            "excluded_embed_metadata_keys": node.excluded_embed_metadata_keys,
            "excluded_llm_metadata_keys": node.excluded_llm_metadata_keys,
        }
        serialized_nodes.append(node_dict)

    json_path = target_dir / "all_chunks.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(serialized_nodes, f, indent=2, ensure_ascii=False)

    # 2. Export human-readable text preview file
    text_preview_path = target_dir / "chunks_preview.txt"
    with open(text_preview_path, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write(f" NEXACORE KNOWLEDGE BASE RAG - CHUNK NODES DUMP ({len(nodes)} Chunks)\n")
        f.write("=" * 80 + "\n\n")

        for idx, node in enumerate(nodes, 1):
            f.write(f"--- CHUNK {idx:03d} | NODE ID: {node.node_id} ---\n")
            f.write(f"Source       : {node.metadata.get('source')}\n")
            f.write(f"Department   : {node.metadata.get('department')}\n")
            f.write(f"Document Type: {node.metadata.get('document_type')}\n")
            f.write(f"Section      : {node.metadata.get('section')}\n")
            f.write(f"Header Path  : {node.metadata.get('header_path')}\n")
            f.write(f"Chunk Type   : {node.metadata.get('chunk_type')}\n")
            f.write(f"Text Content :\n{node.text.strip()}\n")
            f.write("-" * 80 + "\n\n")

    logger.info(
        f"Saved {len(nodes)} chunk node(s) to directory '{target_dir}' "
        f"[Files: 'all_chunks.json', 'chunks_preview.txt']"
    )
    return target_dir


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=r"d:\RAG\.env")

    from document_cleaner import DocumentCleaner
    from document_loader import DocumentLoader
    from document_parser import DocumentParser

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    loader = DocumentLoader()
    parser = DocumentParser()
    cleaner = DocumentCleaner()
    hybrid_chunker = HybridChunker()

    raw_docs = loader.load_documents()
    enriched_docs = parser.enrich_all_documents(raw_docs)
    cleaned_docs = cleaner.clean_all_documents(enriched_docs)

    hybrid_nodes = hybrid_chunker.parse_all_documents(cleaned_docs)

    print("\n" + "=" * 80)
    print(f" HYBRID (STRUCTURE + SEMANTIC) CHUNKING SUMMARY ({len(hybrid_nodes)} Nodes)")
    print("=" * 80)
    for node in hybrid_nodes[:3]:
        print(f"\n--- NODE ID: {node.node_id} ---")
        print(f" Source      : {node.metadata.get('source')}")
        print(f" Department  : {node.metadata.get('department')}")
        print(f" Section     : {node.metadata.get('section')}")
        print(f" Chunk Type  : {node.metadata.get('chunk_type')}")
        print(f" Text Snippet: {repr(node.text[:150])}...")
