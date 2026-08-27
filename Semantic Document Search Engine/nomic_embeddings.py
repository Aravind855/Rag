"""
Nomic (nomic-ai/nomic-embed-text-v1) Embedding Generator & Dense Retrieval Module

This script loads cleaned structural units from normalized outputs,
generates dense vector embeddings using Hugging Face AutoTokenizer and AutoModel
with nomic-ai/nomic-embed-text-v1 (trust_remote_code=True), and performs Top-K search.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("NomicEmbeddings")


def mean_pooling(model_output, attention_mask):
    """Mean pooling over unpadded tokens."""
    token_embeddings = model_output[0]  # First element contains all token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)


class NomicEmbeddingGenerator:
    """Embedding generator using nomic-ai/nomic-embed-text-v1 transformer model."""

    MODEL_NAME = "nomic-ai/nomic-embed-text-v1"
    QUERY_PREFIX = "search_query: "
    DOCUMENT_PREFIX = "search_document: "

    def __init__(self, model_name: str = MODEL_NAME, device: Optional[str] = None):
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Loading tokenizer & model '{self.model_name}' (trust_remote_code=True) on device: {self.device}...")

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
        
        try:
            if self.device == "cuda":
                self.model = AutoModel.from_pretrained(self.model_name, trust_remote_code=True, device_map="auto")
            else:
                self.model = AutoModel.from_pretrained(self.model_name, trust_remote_code=True).to(self.device)
        except Exception as e:
            logger.warning(f"Failed loading with device_map='auto': {e}. Falling back to standard device allocation.")
            self.model = AutoModel.from_pretrained(self.model_name, trust_remote_code=True).to(self.device)

        self.model.eval()
        logger.info("Nomic Model and tokenizer successfully loaded.")

    def encode(self, texts: List[str], batch_size: int = 16, is_query: bool = False) -> np.ndarray:
        """Generate normalized vector embeddings for a list of text strings.

        Args:
            texts: List of text strings to embed.
            batch_size: Number of texts per batch.
            is_query: If True, prepends 'search_query: ', otherwise prepends 'search_document: '.

        Returns:
            np.ndarray of shape (len(texts), 768) normalized to unit length (L2).
        """
        if not texts:
            return np.empty((0, 768), dtype=np.float32)

        prefix = self.QUERY_PREFIX if is_query else self.DOCUMENT_PREFIX
        processed_texts = []
        for t in texts:
            clean_text = t.strip()
            if not clean_text.startswith(self.QUERY_PREFIX) and not clean_text.startswith(self.DOCUMENT_PREFIX):
                clean_text = prefix + clean_text
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
                # Mean pooling across sequence dimension
                sentence_embeddings = mean_pooling(model_output, encoded_input['attention_mask'])
                # L2 normalize
                sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)

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
    """Compute Top-K document matches for a given query vector."""
    if metric in ["cosine", "dot"]:
        scores = np.dot(doc_vectors, query_vector)
    elif metric == "euclidean":
        distances = np.linalg.norm(doc_vectors - query_vector, axis=1)
        scores = 1.0 / (1.0 + distances)
    else:
        raise ValueError(f"Unsupported metric: {metric}")

    top_k_indices = np.argsort(scores)[::-1][:top_k]
    return [(int(idx), float(scores[idx])) for idx in top_k_indices]


def run_nomic_pipeline(
    summary_path: Path,
    output_embeddings_path: Path,
    batch_size: int = 16
):
    """Full pipeline: Load dataset -> Generate Nomic Embeddings -> Save -> Run Test Queries."""
    logger.info("--- STARTING NOMIC EMBEDDING PIPELINE ---")
    
    # 1. Load units
    units = load_normalized_dataset(summary_path)
    logger.info(f"Loaded {len(units)} structural units from dataset.")

    # 2. Instantiate Nomic Model
    embedder = NomicEmbeddingGenerator(model_name="nomic-ai/nomic-embed-text-v1")

    # 3. Generate document embeddings
    doc_contents = [u["content"] for u in units]
    logger.info(f"Generating Nomic embeddings for {len(doc_contents)} document units (batch_size={batch_size})...")
    
    start_time = time.time()
    embeddings = embedder.encode(doc_contents, batch_size=batch_size, is_query=False)
    elapsed_time = time.time() - start_time

    logger.info(f"Successfully generated Nomic embeddings. Shape: {embeddings.shape} in {elapsed_time:.2f} seconds.")

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
    logger.info(f"Saved Nomic embeddings to: {output_embeddings_path}")

    # 5. Run Demo Queries & Dense Retrieval Comparison
    test_queries = [
        "What are the remote work policy guidelines for employees?",
        "How do we deploy services in engineering?",
        "Security incident response procedure and access control",
    ]

    print("\n" + "=" * 80)
    print("     NOMIC EMBEDDING DENSE RETRIEVAL DEMO & TOP-K SEARCH RESULTS")
    print("=" * 80)

    for query in test_queries:
        print(f"\nQUERY: '{query}'")
        print("-" * 80)
        
        # Generate query vector
        query_vec = embedder.encode([query], is_query=True)[0]

        # Top-3 Cosine Similarity Search
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
    print("Nomic Embedding Pipeline Complete!")
    print("=" * 80)


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    summary_json_path = base_dir / "normalized_outputs" / "normalized_dataset_summary.json"
    output_nomic_json_path = Path(__file__).resolve().parent / "nomic_embeddings.json"

    run_nomic_pipeline(summary_json_path, output_nomic_json_path)
