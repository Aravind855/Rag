"""
FAISS Vector Similarity Search Module for NexaCore Semantic Document Search.

Builds a FAISS index (IndexFlatIP for Cosine Similarity) over chunk embeddings,
maintaining metadata mapping and executing top-k semantic similarity search queries.
"""

import json
import logging
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import faiss
import numpy as np

sys.path.append(str(Path(__file__).resolve().parent.parent))
from document_chunker import DocumentChunk
from document_embedder import DocumentEmbedder, EmbeddedChunk

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Dataclass holding FAISS similarity search result item."""
    score: float
    chunk_id: str
    text: str
    page_number: int
    total_pages: int
    source_file: str
    file_path: str
    category: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert search result to dictionary format."""
        return asdict(self)


class FAISSVectorIndex:
    """FAISS-backed vector similarity search index with metadata mapping."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        # Use IndexFlatIP (Inner Product) for Cosine Similarity with normalized vectors
        self.index = faiss.IndexFlatIP(dimension)
        self.metadata_store: List[DocumentChunk] = []
        logger.info(f"Initialized FAISS IndexFlatIP with dimension {dimension}.")

    def add_embeddings(self, embedded_chunks: List[EmbeddedChunk]) -> None:
        """Add embedded chunks and their vectors to the FAISS index."""
        if not embedded_chunks:
            logger.warning("No embedded chunks provided to FAISS index.")
            return

        # Stack vectors into a float32 2D NumPy array
        vectors = np.array([ec.embedding for ec in embedded_chunks], dtype=np.float32)

        if vectors.shape[1] != self.dimension:
            self.dimension = vectors.shape[1]
            self.index = faiss.IndexFlatIP(self.dimension)

        faiss.normalize_L2(vectors)

        self.index.add(vectors)
        self.metadata_store.extend([ec.chunk for ec in embedded_chunks])
        logger.info(f"Added {len(embedded_chunks)} vectors to FAISS index. Total indexed vectors: {self.index.ntotal}")

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        category_filter: Optional[str] = None,
    ) -> List[SearchResult]:
        """Search top-k most similar chunks for a given query vector.

        Args:
            query_vector: 1D or 2D NumPy float32 vector embedding of the query.
            top_k: Number of top results to return.
            category_filter: Optional category filter (e.g., 'engineering', 'hr').

        Returns:
            List of SearchResult objects ordered by cosine similarity score.
        """
        if self.index.ntotal == 0:
            logger.warning("FAISS index is empty.")
            return []

        query_arr = np.array(query_vector, dtype=np.float32)
        if query_arr.ndim == 1:
            query_arr = np.expand_dims(query_arr, axis=0)

        faiss.normalize_L2(query_arr)

        search_k = min(top_k * 3 if category_filter else top_k, self.index.ntotal)
        scores, indices = self.index.search(query_arr, search_k)

        results: List[SearchResult] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata_store):
                continue

            chunk = self.metadata_store[idx]

            if category_filter and chunk.category.lower() != category_filter.lower():
                continue

            res = SearchResult(
                score=float(score),
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                page_number=chunk.page_number,
                total_pages=chunk.total_pages,
                source_file=chunk.source_file,
                file_path=chunk.file_path,
                category=chunk.category,
            )
            results.append(res)

            if len(results) >= top_k:
                break

        return results

    def search_query(
        self,
        query_text: str,
        embedder: DocumentEmbedder,
        top_k: int = 5,
        category_filter: Optional[str] = None,
    ) -> List[SearchResult]:
        """Convenience method: Embed query string and execute FAISS similarity search."""
        query_vec = embedder.embed_query(query_text)
        return self.search(query_vec, top_k=top_k, category_filter=category_filter)

    def save(self, dir_path: Union[str, Path] = r"d:\RAG\faiss_index") -> None:
        """Save FAISS index and metadata store to directory."""
        path = Path(dir_path).resolve()
        path.mkdir(parents=True, exist_ok=True)

        faiss_file = str(path / "index.faiss")
        meta_file = str(path / "metadata.json")

        faiss.write_index(self.index, faiss_file)
        meta_data = [c.to_dict() for c in self.metadata_store]
        Path(meta_file).write_text(json.dumps(meta_data, indent=2, ensure_ascii=False), encoding="utf-8")

        logger.info(f"Saved FAISS index and metadata to '{path}'")

    @classmethod
    def load(cls, dir_path: Union[str, Path] = r"d:\RAG\faiss_index") -> "FAISSVectorIndex":
        """Load FAISS index and metadata store from directory."""
        path = Path(dir_path).resolve()
        faiss_file = str(path / "index.faiss")
        meta_file = str(path / "metadata.json")

        if not Path(faiss_file).exists() or not Path(meta_file).exists():
            raise FileNotFoundError(f"FAISS index files not found in '{path}'")

        index = faiss.read_index(faiss_file)
        meta_data_raw = json.loads(Path(meta_file).read_text(encoding="utf-8"))

        instance = cls(dimension=index.d)
        instance.index = index
        instance.metadata_store = [DocumentChunk(**item) for item in meta_data_raw]

        logger.info(f"Loaded FAISS index with {index.ntotal} vectors from '{path}'")
        return instance


if __name__ == "__main__":
    from document_chunker import RecursiveDocumentChunker
    from document_cleaner import PDFDocumentCleaner
    from document_loader import PDFDocumentLoader
    from document_parser import PDFDocumentParser

    logging.basicConfig(level=logging.INFO)
    loader = PDFDocumentLoader()
    parser = PDFDocumentParser()
    cleaner = PDFDocumentCleaner()
    chunker = RecursiveDocumentChunker(chunk_size=800, chunk_overlap=150)
    embedder = DocumentEmbedder()

    loaded_pdfs = loader.load_all_pdfs()
    parsed_pages = parser.parse_all_documents(loaded_pdfs)
    cleaned_pages = cleaner.clean_all_pages(parsed_pages)
    chunks = chunker.chunk_all_pages(cleaned_pages)
    embedded_chunks = embedder.embed_all_chunks(chunks)

    vector_index = FAISSVectorIndex()
    vector_index.add_embeddings(embedded_chunks)

    query = "What is the deployment model for production environments?"
    logger.info(f"Testing Query: '{query}'")
    results = vector_index.search_query(query, embedder, top_k=3)

    print(f"\nTop {len(results)} Search Results for '{query}':")
    for r in results:
        print(f"\n- [Score: {r.score:.4f}] {r.source_file} (Page {r.page_number}) | Category: {r.category}")
        print(f"  Snippet: {r.text[:200]}...")

    for pdf in loaded_pdfs:
        pdf.close()
