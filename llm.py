"""
LLM Provider Configuration & Factory Module for RAG Applications.

This module provides factory functions to instantiate Chat LLMs across multiple providers
(Groq, DeepSeek, OpenRouter, NVIDIA, Mistral, Google Gemini, OpenAI, Anthropic, Ollama).
API keys, provider choice, and default models are all configurable via environment variables
or runtime arguments.
"""

import logging
import os
from typing import Any, Dict, Optional

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure Module Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Standard Provider Imports with graceful fallback check
try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

try:
    from langchain_mistralai import ChatMistralAI
except ImportError:
    ChatMistralAI = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

try:
    from langchain_community.chat_models import ChatOllama
except ImportError:
    ChatOllama = None


class ConfigSettings:
    """Centralized environment settings for LLM models and API credentials."""

    # Default Provider and Controls
    @property
    def DEFAULT_PROVIDER(self) -> str:
        return os.getenv("LLM_PROVIDER", "groq")

    @property
    def DEFAULT_TEMPERATURE(self) -> float:
        return float(os.getenv("LLM_TEMPERATURE", "0.7"))

    @property
    def LLM_MAX_RETRIES(self) -> int:
        return int(os.getenv("LLM_MAX_RETRIES", "3"))

    # API Keys
    @property
    def GROQ_API_KEY(self) -> Optional[str]:
        return os.getenv("GROQ_API_KEY")

    @property
    def DEEPSEEK_API_KEY(self) -> Optional[str]:
        return os.getenv("DEEPSEEK_API_KEY")

    @property
    def OPENROUTER_API_KEY(self) -> Optional[str]:
        return os.getenv("OPENROUTER_API_KEY")

    @property
    def NVIDIA_API_KEY(self) -> Optional[str]:
        return os.getenv("NVIDIA_API_KEY")

    @property
    def MISTRAL_API_KEY(self) -> Optional[str]:
        return os.getenv("MISTRAL_API_KEY")

    @property
    def GEMINI_API_KEY(self) -> Optional[str]:
        return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    @property
    def OPENAI_API_KEY(self) -> Optional[str]:
        return os.getenv("OPENAI_API_KEY")

    @property
    def ANTHROPIC_API_KEY(self) -> Optional[str]:
        return os.getenv("ANTHROPIC_API_KEY")

    # Default Models
    @property
    def GROQ_MODEL(self) -> str:
        return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    @property
    def DEEPSEEK_MODEL(self) -> str:
        return os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    @property
    def OPENROUTER_MODEL(self) -> str:
        return os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-haiku")

    @property
    def NVIDIA_MODEL(self) -> str:
        return os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b")

    @property
    def MISTRAL_MODEL(self) -> str:
        return os.getenv("MISTRAL_MODEL", "mistral-medium-2505")

    @property
    def GEMINI_MODEL(self) -> str:
        return os.getenv("GEMINI_MODEL", "gemma-4-26b-a4b-it")

    @property
    def OPENAI_MODEL(self) -> str:
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    @property
    def ANTHROPIC_MODEL(self) -> str:
        return os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    @property
    def OLLAMA_MODEL(self) -> str:
        return os.getenv("OLLAMA_MODEL", "llama3")

    @property
    def OLLAMA_BASE_URL(self) -> str:
        return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


# Global Settings Singleton
settings = ConfigSettings()


# ==============================================================================
# Individual LLM Provider Initializers
# ==============================================================================

def get_groq_llm(
    temperature: float = 0.7,
    json_mode: bool = False,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    ):
    """Initialize Groq LLM with configurable model and API key."""
    if ChatGroq is None:
        raise ImportError("langchain-groq package missing. Install with `pip install langchain-groq`.")

    key_to_use = api_key if api_key else settings.GROQ_API_KEY
    if not key_to_use:
        raise ValueError("GROQ_API_KEY not set in environment.")

    model_to_use = model if model else settings.GROQ_MODEL
    kwargs: Dict[str, Any] = dict(
        groq_api_key=key_to_use,
        model=model_to_use,
        temperature=temperature,
        max_tokens=4096,
        timeout=60,
        max_retries=settings.LLM_MAX_RETRIES,
    )
    if json_mode:
        kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}

    return ChatGroq(**kwargs)


def get_deepseek_llm(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.2,
    ):
    """Configure DeepSeek LLM with settings or provided key/model."""
    if ChatOpenAI is None:
        raise ImportError("langchain-openai package missing. Install with `pip install langchain-openai`.")

    key_to_use = api_key if api_key else settings.DEEPSEEK_API_KEY
    if not key_to_use:
        raise ValueError("DEEPSEEK_API_KEY not set in environment.")

    model_to_use = model if model else settings.DEEPSEEK_MODEL
    return ChatOpenAI(
        model=model_to_use,
        temperature=temperature,
        openai_api_key=key_to_use,
        openai_api_base="https://api.deepseek.com/v1",
    )


def get_openrouter_llm(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    ):
    """Configure OpenRouter LLM with settings or provided key/model."""
    if ChatOpenAI is None:
        raise ImportError("langchain-openai package missing. Install with `pip install langchain-openai`.")

    key_to_use = api_key if api_key else settings.OPENROUTER_API_KEY
    if not key_to_use:
        raise ValueError("OPENROUTER_API_KEY not set in environment.")

    model_to_use = model if model else settings.OPENROUTER_MODEL
    return ChatOpenAI(
        model=model_to_use,
        temperature=temperature,
        openai_api_key=key_to_use,
        openai_api_base="https://openrouter.ai/api/v1",
    )


def get_nvidia_llm(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.5,
    ):
    """Configure NVIDIA-hosted chat model with settings or provided key/model."""
    if ChatOpenAI is None:
        raise ImportError("langchain-openai package missing. Install with `pip install langchain-openai`.")

    key_to_use = api_key if api_key else settings.NVIDIA_API_KEY
    if not key_to_use:
        raise ValueError("NVIDIA_API_KEY not set in environment.")

    model_to_use = model if model else settings.NVIDIA_MODEL
    return ChatOpenAI(
        api_key=key_to_use,
        base_url="https://integrate.api.nvidia.com/v1",
        model=model_to_use,
        temperature=temperature,
        max_tokens=32768,
    )


def get_mistral_llm(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    ):
    """Configure Mistral LLM with settings or provided key/model."""
    if ChatMistralAI is None:
        raise ImportError("langchain-mistralai package missing. Install with `pip install langchain-mistralai`.")

    key_to_use = api_key if api_key else settings.MISTRAL_API_KEY
    if not key_to_use:
        raise ValueError("Mistral API key not set in environment (MISTRAL_API_KEY).")

    model_to_use = model if model else settings.MISTRAL_MODEL
    return ChatMistralAI(
        model=model_to_use,
        api_key=key_to_use,
        temperature=temperature,
    )


def get_gemini_llm(
    temperature: float = 0.2,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    fallback_to_system: bool = True,
    ):
    """Configure Google Gemini LLM with settings or provided key/model."""
    if ChatGoogleGenerativeAI is None:
        raise ImportError("langchain-google-genai package missing. Install with `pip install langchain-google-genai`.")

    key_to_use = api_key if api_key else (settings.GEMINI_API_KEY if fallback_to_system else None)
    if not key_to_use:
        raise ValueError("Please set GEMINI_API_KEY or GOOGLE_API_KEY in the environment.")

    model_to_use = model if model else settings.GEMINI_MODEL
    return ChatGoogleGenerativeAI(
        model=model_to_use,
        google_api_key=key_to_use,
        temperature=temperature,
    )


def get_openai_llm(
    temperature: float = 0.7,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    ):
    """Configure OpenAI LLM."""
    if ChatOpenAI is None:
        raise ImportError("langchain-openai package missing. Install with `pip install langchain-openai`.")

    key_to_use = api_key if api_key else settings.OPENAI_API_KEY
    if not key_to_use:
        raise ValueError("OPENAI_API_KEY not set in environment.")

    model_to_use = model if model else settings.OPENAI_MODEL
    return ChatOpenAI(
        model=model_to_use,
        temperature=temperature,
        api_key=key_to_use,
    )


def get_anthropic_llm(
    temperature: float = 0.7,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    ):
    """Configure Anthropic Claude LLM."""
    if ChatAnthropic is None:
        raise ImportError("langchain-anthropic package missing. Install with `pip install langchain-anthropic`.")

    key_to_use = api_key if api_key else settings.ANTHROPIC_API_KEY
    if not key_to_use:
        raise ValueError("ANTHROPIC_API_KEY not set in environment.")

    model_to_use = model if model else settings.ANTHROPIC_MODEL
    return ChatAnthropic(
        model=model_to_use,
        temperature=temperature,
        api_key=key_to_use,
    )


def get_ollama_llm(
    model: Optional[str] = None,
    temperature: float = 0.7,
    base_url: Optional[str] = None,
    ):
    """Configure local Ollama chat model."""
    if ChatOllama is None:
        raise ImportError("langchain-community package missing. Install with `pip install langchain-community`.")

    model_to_use = model if model else settings.OLLAMA_MODEL
    base_url_to_use = base_url if base_url else settings.OLLAMA_BASE_URL
    return ChatOllama(
        model=model_to_use,
        temperature=temperature,
        base_url=base_url_to_use,
    )


# ==============================================================================
# Centralized Factory Function
# ==============================================================================

def get_llm(
    provider: Optional[str] = None,
    temperature: Optional[float] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs: Any,
    ):
    """Universal factory function to retrieve LLM instance based on provider name.

    If provider is omitted, the function defaults to `LLM_PROVIDER` in environment variables.

    Args:
        provider: Provider identifier ('groq', 'deepseek', 'openrouter', 'nvidia',
                  'mistral', 'gemini', 'google', 'openai', 'anthropic', 'ollama').
        temperature: Controls model output randomness. Defaults to env LLM_TEMPERATURE or 0.7.
        model: Model identifier override.
        api_key: API key override.
        **kwargs: Additional provider-specific keyword arguments.

    Returns:
        Configured LangChain Chat LLM model instance.
    """
    provider_name = (provider or settings.DEFAULT_PROVIDER).lower().strip()
    temp_val = temperature if temperature is not None else settings.DEFAULT_TEMPERATURE

    provider_map = {
        "groq": lambda: get_groq_llm(temperature=temp_val, api_key=api_key, model=model, **kwargs),
        "deepseek": lambda: get_deepseek_llm(api_key=api_key, model=model, temperature=temp_val),
        "openrouter": lambda: get_openrouter_llm(api_key=api_key, model=model, temperature=temp_val),
        "nvidia": lambda: get_nvidia_llm(api_key=api_key, model=model, temperature=temp_val),
        "mistral": lambda: get_mistral_llm(api_key=api_key, model=model, temperature=temp_val),
        "gemini": lambda: get_gemini_llm(temperature=temp_val, api_key=api_key, model=model),
        "google": lambda: get_gemini_llm(temperature=temp_val, api_key=api_key, model=model),
        "openai": lambda: get_openai_llm(temperature=temp_val, api_key=api_key, model=model),
        "anthropic": lambda: get_anthropic_llm(temperature=temp_val, api_key=api_key, model=model),
        "ollama": lambda: get_ollama_llm(model=model, temperature=temp_val, **kwargs),
    }

    if provider_name not in provider_map:
        supported = ", ".join(sorted(set(provider_map.keys())))
        raise ValueError(f"Unsupported LLM provider '{provider_name}'. Supported providers: {supported}")

    logger.info("Initializing LLM provider '%s' (Model: %s)", provider_name, model or "default")
    return provider_map[provider_name]()


if __name__ == "__main__":
    print(f"Default LLM Provider from env: {settings.DEFAULT_PROVIDER}")
    print("LLM Provider module loaded successfully.")
