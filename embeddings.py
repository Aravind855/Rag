"""
Embedding Provider Configurations for RAG Applications.

This module configures multiple embedding providers (SentenceTransformers, HuggingFace, etc.)
and allows seamless model switching for RAG pipelines using environment variables or
explicit configuration parameters, following the same architectural pattern as llm.py.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Load environment variables from root .env file if available
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    pass

# Configure Module Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Standard Provider Imports with graceful fallback checks
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None


class ConfigSettings:
    """Settings class to manage environment configurations for Embedding providers."""

    @property
    def DEFAULT_PROVIDER(self) -> str:
        return os.getenv("EMBEDDING_PROVIDER", "sentence_transformer")

    @property
    def EMBEDDING_DEVICE(self) -> str:
        return os.getenv("EMBEDDING_DEVICE", "cpu")

    @property
    def SENTENCE_TRANSFORMER_MODEL(self) -> str:
        return os.getenv(
            "SENTENCE_TRANSFORMER_EMBEDDING",
            os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        )


# Global Settings Singleton
settings = ConfigSettings()


# ==============================================================================
# Individual Embedding Provider Initializers
# ==============================================================================

def get_sentence_transformer_embedding(
    model: Optional[str] = None,
    device: Optional[str] = None,
) -> SentenceTransformer:
    """Configure SentenceTransformer embedding model with settings or provided model/device."""
    if SentenceTransformer is None:
        raise ImportError(
            "sentence-transformers package missing. Install it using `pip install sentence-transformers`."
        )

    model_to_use = model if model else settings.SENTENCE_TRANSFORMER_MODEL
    device_to_use = device if device else settings.EMBEDDING_DEVICE

    logger.info(f"Initializing SentenceTransformer model '{model_to_use}' on device '{device_to_use}'...")
    return SentenceTransformer(model_name_or_path=model_to_use, device=device_to_use)


# ==============================================================================
# Centralized Factory Function
# ==============================================================================

def get_embedding_model(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    device: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    """Universal factory function to switch between Embedding models on demand.

    If provider is omitted, the function defaults to `EMBEDDING_PROVIDER` in environment variables.

    Args:
        provider: Provider identifier ('sentence_transformer', 'sentence_transformers', 'huggingface').
        model: Model identifier override.
        device: Compute device ('cpu', 'cuda', 'auto').
        **kwargs: Additional provider-specific keyword arguments.

    Returns:
        Configured Embedding model instance.
    """
    provider_name = (provider or settings.DEFAULT_PROVIDER).lower().strip()

    if provider_name in ("sentence_transformer", "sentence_transformers", "huggingface", "minilm"):
        return get_sentence_transformer_embedding(model=model, device=device)
    else:
        supported = ["sentence_transformer"]
        raise ValueError(
            f"Unsupported embedding provider '{provider_name}'. Supported options: {', '.join(supported)}"
        )


if __name__ == "__main__":
    print(f"Default Embedding Provider from env: {settings.DEFAULT_PROVIDER}")
    print(f"Default Sentence Transformer Model: {settings.SENTENCE_TRANSFORMER_MODEL}")
    print("Embedding Provider module loaded successfully.")
