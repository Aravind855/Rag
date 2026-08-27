"""
Document Embedding Module for NexaCore Semantic Document Search.

Generates dense vector embeddings for DocumentChunk objects using the
configured SentenceTransformer embedding model.
"""

import logging
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

# Ensure parent directory is in path to import embeddings.py
sys.path.append(str(Path(__file__).resolve().parent.parent))
from embeddings import get_embedding_model
from document_chunker import DocumentChunk

logger = logging.getLogger(__name__)


@dataclass
class EmbeddedChunk:
    """Document chunk paired with its dense vector embedding."""
    chunk: DocumentChunk
    embedding: np.ndarray

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk metadata and embedding into dictionary format."""
        data = self.chunk.to_dict()
        data["embedding_dim"] = len(self.embedding)
        return data


class DocumentEmbedder:
    """Generates vector embeddings for DocumentChunk lists using SentenceTransformers."""

    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        logger.info("Initializing DocumentEmbedder...")
        self.embedding_model = get_embedding_model(model_name=model_name, device=device)

    def embed_chunk(self, chunk: DocumentChunk) -> EmbeddedChunk:
        """Generate vector embedding for a single DocumentChunk."""
        vector = self.embedding_model.encode(
            chunk.text,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return EmbeddedChunk(chunk=chunk, embedding=vector)

    def embed_all_chunks(self, chunks: List[DocumentChunk], batch_size: int = 32) -> List[EmbeddedChunk]:
        """Generate vector embeddings for a list of DocumentChunks in batches."""
        if not chunks:
            logger.warning("No chunks provided for embedding.")
            return []

        logger.info(f"Generating embeddings for {len(chunks)} text chunks (Batch size: {batch_size})...")
        texts = [c.text for c in chunks]

        # Generate embeddings in batch
        vectors = self.embedding_model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        embedded_chunks: List[EmbeddedChunk] = []
        for chunk, vector in zip(chunks, vectors):
            embedded_chunks.append(EmbeddedChunk(chunk=chunk, embedding=vector))

        logger.info(
            f"Successfully embedded {len(embedded_chunks)} chunks. Vector dimension: {vectors.shape[1]}"
        )
        return embedded_chunks

    def embed_query(self, query: str) -> np.ndarray:
        """Generate vector embedding for a search query string."""
        return self.embedding_model.encode(
            query,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    embedder = DocumentEmbedder()
    test_vec = embedder.embed_query("NexaCore Deployment Policy")
    print(f"Test Query Embedding Vector Shape: {test_vec.shape}")
