"""
BGE (BAAI/bge-large-en) Embedding Generator & Dense Retrieval Module

This script loads cleaned structural units from normalized outputs,
generates dense vector embeddings using Hugging Face AutoTokenizer and AutoModel
with BAAI/bge-large-en, and performs Top-K semantic similarity search.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("BGEEmbeddings")


class BGEEmbeddingGenerator:
    """Embedding generator using BAAI/bge-large-en transformer model."""

    MODEL_NAME = "BAAI/bge-large-en"
    DEFAULT_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

    def __init__(self, model_name: str = MODEL_NAME, device: Optional[str] = None):
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Loading tokenizer & model '{self.model_name}' on device: {self.device}...")

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        
        # Try loading with device_map="auto", fallback to explicit device if needed
        try:
            if self.device == "cuda":
                self.model = AutoModel.from_pretrained(self.model_name, device_map="auto")
            else:
                self.model = AutoModel.from_pretrained(self.model_name).to(self.device)
        except Exception as e:
            logger.warning(f"Failed loading with device_map='auto': {e}. Falling back to standard device allocation.")
            self.model = AutoModel.from_pretrained(self.model_name).to(self.device)

        self.model.eval()
        logger.info("Model and tokenizer successfully loaded.")

    def encode(self, texts: List[str], batch_size: int = 16, is_query: bool = False) -> np.ndarray:
        """Generate normalized vector embeddings for a list of text strings.

        Args:
            texts: List of text strings to embed.
            batch_size: Number of texts per batch.
            is_query: If True, prepends the BGE query instruction prefix.

        Returns:
            np.ndarray of shape (len(texts), embedding_dim) normalized to unit length (L2).
        """
        if not texts:
            return np.empty((0, 1024), dtype=np.float32)

        processed_texts = []
        for t in texts:
            clean_text = t.strip()
            if is_query and not clean_text.startswith(self.DEFAULT_QUERY_PREFIX):
                clean_text = self.DEFAULT_QUERY_PREFIX + clean_text
            processed_texts.append(clean_text)

        all_embeddings = []

        total_batches = (len(processed_texts) - 1) // batch_size + 1
        for i in range(0, len(processed_texts), batch_size):
            batch_num = i // batch_size + 1
            logger.info(f"Encoding batch {batch_num}/{total_batches} ({len(processed_texts[i : i + batch_size])} texts)...")
            batch_texts = processed_texts[i : i + batch_size]
            encoded_input = self.tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )
            
            # Move inputs to model device
            encoded_input = {k: v.to(self.model.device) for k, v in encoded_input.items()}

            with torch.no_grad():
                model_output = self.model(**encoded_input)
                # BGE uses CLS token pooling ([0][:, 0]) as recommended by BAAI
                sentence_embeddings = model_output[0][:, 0]

                # Perform L2 normalization
                sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)

            all_embeddings.append(sentence_embeddings.cpu().numpy())

        return np.vstack(all_embeddings).astype(np.float32)


def load_normalized_dataset(summary_file_path: Path) -> List[Dict[str, Any]]:
    """Flatten and extract structural units from normalized_dataset_summary.json."""
    if not summary_file_path.exists():
        raise FileNotFoundError(f"Dataset summary file not found at: {summary_file_path}")

    with open(summary_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    units = []
    for doc in data.get("documents", []):
        for unit in doc.get("units", []):
            units.append({
                "unit_id": unit.get("unit_id"),
                "file_name": doc.get("file_name"),
                "category": doc.get("category"),
                "breadcrumbs": unit.get("breadcrumbs"),
                "title": unit.get("title"),
                "unit_type": unit.get("unit_type"),
                "content": unit.get("content"),
                "word_count": unit.get("word_count"),
                "char_count": unit.get("char_count"),
            })
    return units


def compute_top_k_similarities(
    query_vector: np.ndarray,
    doc_vectors: np.ndarray,
    top_k: int = 5,
    metric: str = "cosine"
    ) -> List[Tuple[int, float]]:
    """Compute Top-K document matches for a given query vector.

    Args:
        query_vector: 1D array of shape (dim,)
        doc_vectors: 2D array of shape (num_docs, dim)
        top_k: Number of top results to return
        metric: 'cosine', 'dot', or 'euclidean'

    Returns:
        List of tuples (doc_index, similarity_score)
    """
    if metric in ["cosine", "dot"]:
        # Since vectors are L2-normalized, Cosine Similarity == Dot Product
        scores = np.dot(doc_vectors, query_vector)
    elif metric == "euclidean":
        # Euclidean distance = ||u - v||_2; convert to similarity score 1 / (1 + distance)
        distances = np.linalg.norm(doc_vectors - query_vector, axis=1)
        scores = 1.0 / (1.0 + distances)
    else:
        raise ValueError(f"Unsupported metric: {metric}")

    top_k_indices = np.argsort(scores)[::-1][:top_k]
    return [(int(idx), float(scores[idx])) for idx in top_k_indices]


def run_bge_pipeline(
    summary_path: Path,
    output_embeddings_path: Path,
    batch_size: int = 16
    ):
    """Full pipeline: Load dataset -> Generate BGE Embeddings -> Save -> Run Test Queries."""
    logger.info("--- STARTING BGE EMBEDDING PIPELINE ---")
    
    # 1. Load units
    units = load_normalized_dataset(summary_path)
    logger.info(f"Loaded {len(units)} structural units from dataset.")

    # 2. Instantiate BGE Model
    embedder = BGEEmbeddingGenerator(model_name="BAAI/bge-large-en")

    # 3. Generate document embeddings
    doc_contents = [u["content"] for u in units]
    logger.info(f"Generating BGE embeddings for {len(doc_contents)} document units (batch_size={batch_size})...")
    
    start_time = time.time()
    embeddings = embedder.encode(doc_contents, batch_size=batch_size, is_query=False)
    elapsed_time = time.time() - start_time

    logger.info(f"Successfully generated embeddings. Shape: {embeddings.shape} in {elapsed_time:.2f} seconds.")

    # 4. Save metadata + embeddings
    output_data = {
        "model_name": embedder.MODEL_NAME,
        "embedding_dim": int(embeddings.shape[1]),
        "total_units": len(units),
        "generation_time_seconds": round(elapsed_time, 2),
        "units": []
    }

    for i, unit in enumerate(units):
        unit_copy = dict(unit)
        unit_copy["embedding"] = embeddings[i].tolist()
        output_data["units"].append(unit_copy)

    output_embeddings_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_embeddings_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    logger.info(f"Saved BGE embeddings to: {output_embeddings_path}")

    # 5. Run Demo Queries & Dense Retrieval Comparison
    test_queries = [
        "What are the remote work policy guidelines for employees?",
        "How do we deploy services in engineering?",
        "Security incident response procedure and access control",
    ]

    print("\n" + "=" * 80)
    print("      BGE EMBEDDING DENSE RETRIEVAL DEMO & TOP-K SEARCH RESULTS")
    print("=" * 80)

    for query in test_queries:
        print(f"\nQUERY: '{query}'")
        print("-" * 80)
        
        # Generate query vector
        query_vec = embedder.encode([query], is_query=True)[0]

        # Top-5 Cosine Similarity Search
        top_cosine = compute_top_k_similarities(query_vec, embeddings, top_k=3, metric="cosine")
        print("  [Top-3 Cosine Similarity Results]:")
        for rank, (idx, score) in enumerate(top_cosine, 1):
            u = units[idx]
            print(f"    Rank {rank} | Score: {score:.4f} | Unit ID: {u['unit_id']}")
            print(f"      File: {u['file_name']} | Breadcrumbs: {u['breadcrumbs']}")
            snippet = u['content'].replace('\n', ' ')[:120]
            print(f"      Snippet: {snippet}...\n")

        # Top-3 Euclidean Distance Results
        top_euc = compute_top_k_similarities(query_vec, embeddings, top_k=3, metric="euclidean")
        print("  [Top-3 Euclidean Distance Results (Converted Score 1/(1+d))]:")
        for rank, (idx, score) in enumerate(top_euc, 1):
            u = units[idx]
            print(f"    Rank {rank} | Score: {score:.4f} | File: {u['file_name']} (Unit ID: {u['unit_id']})")

    print("\n" + "=" * 80)
    print("BGE Embedding Pipeline Complete!")
    print("=" * 80)


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    summary_json_path = base_dir / "normalized_outputs" / "normalized_dataset_summary.json"
    output_bge_json_path = Path(__file__).resolve().parent / "bge_embeddings.json"

    run_bge_pipeline(summary_json_path, output_bge_json_path)
