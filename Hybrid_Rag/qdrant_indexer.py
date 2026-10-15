"""Qdrant Dense Vector Database Indexing & Retrieval Module for Hybrid RAG.

Configures HNSW (Hierarchical Navigable Small World) graph indexing for dense vector retrieval.
Loads pre-computed Cohere embeddings from d:\RAG\Hybrid_Rag\chunks\embedded_chunks.json,
connects to Qdrant Vector Database (using QDRANT_URL and QDRANT_API_KEY from .env,
with seamless local persistence fallback if the cloud cluster is paused),
configures HNSW index parameters (m, ef_construct, full_scan_threshold),
indexes all 522 chunks, and provides HNSW-based dense similarity retrieval.

All paths are resolved dynamically without hardcoding.
All operations are written as pure procedural functions without classes.
"""

import json
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    HnswConfigDiff,
    PointStruct,
    SearchParams,
    VectorParams,
)

# Functional embedding import
from embeddings import get_cohere_embeddings, load_chunks_from_manifest

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("hybrid_rag.qdrant")

# =====================================================================
# DYNAMIC PATH RESOLUTION & ENVIRONMENT LOADING
# =====================================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

DEFAULT_EMBEDDINGS_CACHE = PROJECT_ROOT / "Hybrid_Rag" / "chunks" / "embedded_chunks.json"
DEFAULT_LOCAL_QDRANT_DIR = PROJECT_ROOT / "Hybrid_Rag" / "qdrant_db"
DEFAULT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "nexacore_dense_chunks")


def get_default_embeddings_cache() -> Path:
    """Returns the dynamically resolved embedded chunks cache path."""
    return DEFAULT_EMBEDDINGS_CACHE


def get_default_local_qdrant_dir() -> Path:
    """Returns the dynamically resolved local Qdrant directory."""
    return DEFAULT_LOCAL_QDRANT_DIR


# =====================================================================
# 1. CLIENT INITIALIZATION (CLOUD WITH PERSISTENT LOCAL FALLBACK)
# =====================================================================
# verified
def get_qdrant_client(
    url: Optional[str] = None,
    api_key: Optional[str] = None,
    local_path: Optional[Union[str, Path]] = None,
    prefer_local: bool = False,
    ) -> Tuple[QdrantClient, str]:
    """Initializes and returns a QdrantClient instance.

    Attempts connection to Qdrant Cloud (QDRANT_URL & QDRANT_API_KEY).
    If the remote cluster is paused, unreachable, or prefer_local=True,
    gracefully connects to persistent local Qdrant storage.

    Returns:
        Tuple of (client_instance, storage_mode_str).
    """
    cloud_url = url or os.getenv("QDRANT_URL")
    cloud_key = api_key or os.getenv("QDRANT_API_KEY")
    storage_dir = Path(local_path).resolve() if local_path else DEFAULT_LOCAL_QDRANT_DIR

    if cloud_url and cloud_key and not prefer_local:
        try:
            logger.info(f"Connecting to Qdrant Cloud at {cloud_url}...")
            client = QdrantClient(
                url=cloud_url,
                api_key=cloud_key,
                timeout=5.0,
                check_compatibility=False,
            )
            # Health check
            client.get_collections()
            logger.info("Successfully connected to remote Qdrant Cloud cluster.")
            return client, "cloud"
        except Exception as e:
            logger.warning(
                f"Qdrant Cloud connection could not be established ({e}). "
                f"Your cloud cluster might be paused in Qdrant Cloud Console (cloud.qdrant.io). "
                f"Falling back seamlessly to persistent local storage at {storage_dir}."
            )

    # Persistent local storage fallback
    storage_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using persistent local Qdrant storage at {storage_dir}...")
    local_client = QdrantClient(path=str(storage_dir))
    return local_client, "local_disk"


# =====================================================================
# 2. HNSW COLLECTION MANAGEMENT
# =====================================================================
# verified
def build_hnsw_config(
    m: int = 16,
    ef_construct: int = 100,
    full_scan_threshold: int = 10,
    on_disk: bool = False,
    ) -> HnswConfigDiff:
    """Builds an HNSW index configuration for Qdrant.

    Args:
        m: Number of bidirectional edges per vector node in the HNSW graph (default: 16).
           Higher values increase recall accuracy at the cost of memory.
        ef_construct: Size of dynamic candidate list during graph construction (default: 100).
           Higher values improve graph quality.
        full_scan_threshold: Minimal vector count to switch from flat scan to HNSW (default: 10, Qdrant minimum >= 10).
           Setting to 10 guarantees HNSW graph indexing is always used for collections with >10 vectors.
        on_disk: If True, stores HNSW graph on disk. If False, keeps in RAM for fastest search.

    Returns:
        HnswConfigDiff object.
    """
    return HnswConfigDiff(
        m=m,
        ef_construct=ef_construct,
        full_scan_threshold=full_scan_threshold,
        on_disk=on_disk,
    )


def ensure_qdrant_collection(
    client: QdrantClient,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    vector_size: int = 2048,
    distance: Distance = Distance.COSINE,
    recreate: bool = False,
    m: int = 16,
    ef_construct: int = 100,
    full_scan_threshold: int = 10,
    on_disk_hnsw: bool = False,
    ) -> bool:
    """Creates the Qdrant collection configured with an explicit HNSW graph index.

    Args:
        client: Active QdrantClient.
        collection_name: Target collection name.
        vector_size: Dimension of embeddings (2048 for Cohere embed-v5.0-fast).
        distance: Distance metric (Cosine).
        recreate: If True, drops and re-creates existing collection.
        m: HNSW graph edges per node (default: 16).
        ef_construct: HNSW build candidate list size (default: 100).
        full_scan_threshold: Threshold to use HNSW (0 = force HNSW on all collection sizes).
        on_disk_hnsw: Whether to store HNSW index on disk (default: False for RAM speed).

    Returns:
        True if collection is ready.
    """
    collections = [c.name for c in client.get_collections().collections]

    if collection_name in collections:
        if recreate:
            logger.info(f"Recreating existing collection '{collection_name}' with new HNSW index...")
            client.delete_collection(collection_name=collection_name)
        else:
            logger.info(f"Collection '{collection_name}' already exists.")
            return True

    hnsw_config = build_hnsw_config(
        m=m,
        ef_construct=ef_construct,
        full_scan_threshold=full_scan_threshold,
        on_disk=on_disk_hnsw,
    )

    logger.info(
        f"Creating HNSW collection '{collection_name}' "
        f"(dim={vector_size}, distance={distance.name}, m={m}, ef_construct={ef_construct}, full_scan_threshold={full_scan_threshold})..."
    )

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=distance),
        hnsw_config=hnsw_config,
    )
    logger.info(f"HNSW collection '{collection_name}' created successfully.")
    return True


# =====================================================================
# 3. DIRECT EMBEDDINGS INGESTION (FROM CACHE JSON)
# =====================================================================

def load_cached_embeddings(
    cache_path: Optional[Union[str, Path]] = None,
    ) -> List[Dict[str, Any]]:
    """Loads pre-computed chunk embeddings directly from embedded_chunks.json."""
    file_path = Path(cache_path).resolve() if cache_path else DEFAULT_EMBEDDINGS_CACHE
    if not file_path.exists():
        raise FileNotFoundError(
            f"Embeddings cache not found at {file_path}. Please run embeddings.py first."
        )

    logger.info(f"Loading pre-computed embeddings from {file_path}...")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = data.get("chunks", [])
    logger.info(f"Loaded {len(chunks)} pre-computed embedded chunks.")
    return chunks


def index_embedded_chunks_to_qdrant(
    client: QdrantClient,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    chunks_data: Optional[List[Dict[str, Any]]] = None,
    cache_path: Optional[Union[str, Path]] = None,
    batch_size: int = 100,
    recreate: bool = False,
    m: int = 16,
    ef_construct: int = 100,
    full_scan_threshold: int = 10,
    ) -> Dict[str, Any]:
    """Uploads pre-computed embedded chunks into Qdrant and constructs the HNSW index.

    Zero re-computation: uses existing 2048-dim vectors from embedded_chunks.json!

    Args:
        client: Connected QdrantClient.
        collection_name: Target collection name.
        chunks_data: Optional list of embedded chunk dictionaries.
        cache_path: Path to embedded_chunks.json if chunks_data is not provided.
        batch_size: Upsert batch size (default: 100).
        recreate: If True, drops and rebuilds the collection with HNSW config.
        m: HNSW edges per node.
        ef_construct: HNSW build candidate list.
        full_scan_threshold: Threshold to activate HNSW.

    Returns:
        Summary statistics dictionary.
    """
    items = chunks_data if chunks_data is not None else load_cached_embeddings(cache_path)
    if not items:
        raise ValueError("No embedded chunks to index into Qdrant.")

    dim = items[0].get("embedding_dimension", len(items[0].get("embedding", [])))

    ensure_qdrant_collection(
        client,
        collection_name=collection_name,
        vector_size=dim,
        recreate=recreate,
        m=m,
        ef_construct=ef_construct,
        full_scan_threshold=full_scan_threshold,
    )

    logger.info(f"Upserting {len(items)} points into HNSW collection '{collection_name}'...")
    start_time = time.time()

    total_upserted = 0
    total_items = len(items)

    for i in range(0, total_items, batch_size):
        batch = items[i : i + batch_size]
        points: List[PointStruct] = []

        for offset, item in enumerate(batch):
            point_id = i + offset + 1
            vector = item.get("embedding", [])
            content = item.get("content", "")
            meta = item.get("metadata", {})

            # Prepare structured payload preserving all metadata & text
            payload = {
                "page_content": content,
                "chunk_id": item.get("chunk_id", meta.get("chunk_id")),
                "metadata": meta,
                "category": meta.get("category", "general"),
                "source": meta.get("source", ""),
                "document_type": meta.get("document_type", ""),
                "breadcrumbs": meta.get("breadcrumbs", ""),
                "has_table": meta.get("has_table", False),
            }

            points.append(PointStruct(id=point_id, vector=vector, payload=payload))

        client.upsert(collection_name=collection_name, points=points)
        total_upserted += len(points)
        logger.info(f"Upserted batch {total_upserted}/{total_items} points into HNSW index...")

    elapsed = round(time.time() - start_time, 2)
    logger.info(f"Successfully indexed {total_upserted} points into HNSW Qdrant in {elapsed}s.")

    return {
        "status": "success",
        "collection_name": collection_name,
        "total_points": total_upserted,
        "vector_dimension": dim,
        "elapsed_seconds": elapsed,
        "hnsw_config": {
            "m": m,
            "ef_construct": ef_construct,
            "full_scan_threshold": full_scan_threshold,
        },
    }


# =====================================================================
# 4. LANGCHAIN VECTORSTORE & HNSW RETRIEVER FACTORY
# =====================================================================

def get_qdrant_vectorstore(
    client: Optional[QdrantClient] = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    ) -> QdrantVectorStore:
    """Returns a LangChain-compatible QdrantVectorStore instance configured with Cohere embeddings.

    Ready for direct dense retrieval and EnsembleRetriever fusion.
    """
    q_client = client or get_qdrant_client()[0]
    cohere_emb = get_cohere_embeddings()

    return QdrantVectorStore(
        client=q_client,
        collection_name=collection_name,
        embedding=cohere_emb,
    )


def get_qdrant_retriever(
    client: Optional[QdrantClient] = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    k: int = 5,
    hnsw_ef: int = 64,
    ):
    """Returns a LangChain dense retriever instance with HNSW search parameters.

    Args:
        client: Connected QdrantClient.
        collection_name: Collection name.
        k: Top-k documents to retrieve.
        hnsw_ef: Search candidate beam size in the HNSW graph (default: 64).
    """
    vectorstore = get_qdrant_vectorstore(client=client, collection_name=collection_name)
    return vectorstore.as_retriever(
        search_kwargs={
            "k": k,
            "search_params": SearchParams(hnsw_ef=hnsw_ef, exact=False),
        }
    )


# =====================================================================
# 5. DENSE HNSW RETRIEVAL (QUERY SEARCH)
# =====================================================================

def dense_search(
    query: str,
    client: Optional[QdrantClient] = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    k: int = 5,
    hnsw_ef: int = 64,
    ) -> List[Document]:
    """Performs semantic dense vector search using HNSW graph traversal in Qdrant.

    Args:
        query: User search query.
        client: Connected QdrantClient.
        collection_name: Target collection name.
        k: Number of top documents to retrieve.
        hnsw_ef: Size of dynamic candidate list for HNSW search (default: 64).

    Returns:
        List of ranked LangChain Document objects with metadata.
    """
    retriever = get_qdrant_retriever(
        client=client,
        collection_name=collection_name,
        k=k,
        hnsw_ef=hnsw_ef,
    )

    start_time = time.time()
    results = retriever.invoke(query)
    latency_ms = round((time.time() - start_time) * 1000, 2)

    logger.info(f"HNSW search retrieved {len(results)} chunks for query='{query}' in {latency_ms} ms")
    return results


# =====================================================================
# 6. PIPELINE ORCHESTRATOR
# =====================================================================

def run_qdrant_indexing(
    cache_path: Optional[Union[str, Path]] = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    recreate: bool = True,
    k: int = 5,
    m: int = 16,
    ef_construct: int = 100,
    full_scan_threshold: int = 10,
    hnsw_ef: int = 64,
    ) -> Dict[str, Any]:
    """End-to-end procedural indexing pipeline for Dense HNSW Retrieval:

    1. Connects to Qdrant (Cloud or persistent local fallback)
    2. Loads pre-computed embeddings from embedded_chunks.json
    3. Creates collection with explicit HNSW graph index (m, ef_construct, full_scan_threshold)
    4. Indexes all 522 points into the HNSW graph
    5. Executes sample dense retrieval queries using HNSW graph search
    """
    logger.info("=" * 70)
    logger.info("STARTING HYBRID RAG QDRANT HNSW DENSE INDEXING PIPELINE")
    logger.info(f"HNSW Config: m={m}, ef_construct={ef_construct}, full_scan_threshold={full_scan_threshold}")
    logger.info("=" * 70)

    # 1. Connect
    client, mode = get_qdrant_client()
    logger.info(f"Qdrant Storage Mode: {mode.upper()}")

    # 2. Ensure collection with HNSW & Index points
    stats = index_embedded_chunks_to_qdrant(
        client=client,
        collection_name=collection_name,
        cache_path=cache_path,
        recreate=recreate,
        m=m,
        ef_construct=ef_construct,
        full_scan_threshold=full_scan_threshold,
    )

    # 3. Verification dense queries via HNSW search
    test_queries = [
        "What is the maximum reimbursement for domestic airfare?",
        "How to handle a critical security breach or incident?",
        "What are the remote work core collaboration hours?",
    ]

    verification_hits = {}
    for q in test_queries:
        hits = dense_search(
            query=q,
            client=client,
            collection_name=collection_name,
            k=2,
            hnsw_ef=hnsw_ef,
        )
        top = hits[0] if hits else None
        verification_hits[q] = {
            "top_chunk_id": top.metadata.get("chunk_id") if top else None,
            "breadcrumbs": top.metadata.get("breadcrumbs") if top else None,
            "snippet": top.page_content[:120].replace("\n", " ") if top else None,
        }

    logger.info("=" * 70)
    logger.info("[QDRANT HNSW DENSE INDEXING COMPLETE]")
    logger.info(f"Storage Mode         : {mode.upper()}")
    logger.info(f"Collection Name      : {collection_name}")
    logger.info(f"Indexed Chunks       : {stats['total_points']}")
    logger.info(f"Vector Dimension     : {stats['vector_dimension']}")
    logger.info(f"HNSW Parameters      : m={m}, ef_construct={ef_construct}, full_scan_threshold={full_scan_threshold}")
    logger.info("Sample Dense Query Hits:")
    for query, res in verification_hits.items():
        logger.info(f" • '{query}' -> [{res['top_chunk_id']}] {res['snippet']}...")
    logger.info("=" * 70)

    return {
        "status": "success",
        "mode": mode,
        "collection_name": collection_name,
        "total_points": stats["total_points"],
        "hnsw_config": stats["hnsw_config"],
        "verification_hits": verification_hits,
    }


if __name__ == "__main__":
    run_qdrant_indexing()
