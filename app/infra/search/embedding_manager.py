"""
Embedding Model Manager for SalesBoost RAG System.

Supports multiple embedding models with automatic dimension detection
and seamless model switching.
"""
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    import openai
except ImportError:
    openai = None

from core.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingModelInfo:
    """Information about an embedding model."""
    name: str
    dimension: int
    max_seq_length: int
    multilingual: bool
    description: str


# Supported embedding models
EMBEDDING_MODELS: Dict[str, EmbeddingModelInfo] = {
    "all-MiniLM-L6-v2": EmbeddingModelInfo(
        name="all-MiniLM-L6-v2",
        dimension=384,
        max_seq_length=256,
        multilingual=False,
        description="Fast, lightweight, English-only"
    ),
    "paraphrase-multilingual-MiniLM-L12-v2": EmbeddingModelInfo(
        name="paraphrase-multilingual-MiniLM-L12-v2",
        dimension=384,
        max_seq_length=128,
        multilingual=True,
        description="Multilingual, good balance of speed and quality"
    ),
    "shibing624/text2vec-base-chinese": EmbeddingModelInfo(
        name="shibing624/text2vec-base-chinese",
        dimension=768,
        max_seq_length=256,
        multilingual=False,
        description="Chinese-optimized, high quality"
    ),
    "BAAI/bge-m3": EmbeddingModelInfo(
        name="BAAI/bge-m3",
        dimension=1024,
        max_seq_length=8192,
        multilingual=True,
        description="Best quality, multilingual, long context (supports dense + sparse + multi-vector)"
    ),
    "BAAI/bge-base-zh-v1.5": EmbeddingModelInfo(
        name="BAAI/bge-base-zh-v1.5",
        dimension=768,
        max_seq_length=512,
        multilingual=False,
        description="Chinese-optimized BGE model"
    ),
    "text-embedding-3-small": EmbeddingModelInfo(
        name="text-embedding-3-small",
        dimension=1536,
        max_seq_length=8191,
        multilingual=True,
        description="OpenAI embedding (requires API key)"
    ),
}


class EmbeddingModelManager:
    """
    Manages embedding models with automatic dimension detection.

    Features:
    - Multiple model support (SentenceTransformers, OpenAI)
    - Automatic dimension detection
    - Model caching (singleton pattern)
    - Batch processing
    - Normalization support
    """

    _instance: Optional["EmbeddingModelManager"] = None
    _model: Optional[Any] = None
    _model_name: Optional[str] = None

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: str = "cpu",
        normalize: bool = True,
        batch_size: int = 32,
    ):
        """
        Initialize embedding model manager.

        Args:
            model_name: Model name (None = use config)
            device: Device to use ("cpu" or "cuda")
            normalize: Normalize embeddings to unit length
            batch_size: Batch size for encoding
        """
        settings = Settings()

        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.device = device or settings.EMBEDDING_DEVICE
        self.normalize = normalize if normalize is not None else settings.EMBEDDING_NORMALIZE
        self.batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE

        self.model_info = EMBEDDING_MODELS.get(self.model_name)

        if not self.model_info:
            logger.warning(f"Unknown model {self.model_name}, will attempt to load anyway")

        self._load_model()

    def _load_model(self):
        """Load embedding model with caching."""
        # Use singleton pattern for model caching
        if EmbeddingModelManager._model_name == self.model_name and EmbeddingModelManager._model is not None:
            logger.info(f"Using cached embedding model: {self.model_name}")
            return

        if self.model_name == "text-embedding-3-small":
            # OpenAI embedding
            if openai is None:
                raise ImportError("openai is not installed. Install with: pip install openai")

            settings = Settings()
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings")

            openai.api_key = settings.OPENAI_API_KEY
            if settings.OPENAI_BASE_URL:
                openai.api_base = settings.OPENAI_BASE_URL

            EmbeddingModelManager._model = "openai"  # Marker for OpenAI
            EmbeddingModelManager._model_name = self.model_name
            logger.info(f"Initialized OpenAI embedding model: {self.model_name}")

        else:
            # SentenceTransformers model
            if SentenceTransformer is None:
                raise ImportError("sentence-transformers is not installed. Install with: pip install sentence-transformers")

            try:
                logger.info(f"Loading embedding model: {self.model_name}")
                model = SentenceTransformer(self.model_name, device=self.device)

                # Auto-detect dimension
                test_embedding = model.encode("test", convert_to_numpy=True)
                detected_dim = len(test_embedding)

                if self.model_info and detected_dim != self.model_info.dimension:
                    logger.warning(
                        f"Detected dimension {detected_dim} differs from expected {self.model_info.dimension}"
                    )

                EmbeddingModelManager._model = model
                EmbeddingModelManager._model_name = self.model_name

                logger.info(
                    f"Loaded embedding model: {self.model_name} "
                    f"(dimension={detected_dim}, device={self.device})"
                )

            except Exception as e:
                logger.error(f"Failed to load embedding model {self.model_name}: {e}")
                raise

    @classmethod
    def get_instance(
        cls,
        model_name: Optional[str] = None,
        device: str = "cpu",
        normalize: bool = True,
        batch_size: int = 32,
    ) -> "EmbeddingModelManager":
        """Get singleton instance of embedding model manager."""
        if cls._instance is None or (model_name and model_name != cls._model_name):
            cls._instance = cls(model_name, device, normalize, batch_size)
        return cls._instance

    def get_dimension(self) -> int:
        """
        Get embedding dimension.

        Returns:
            Embedding dimension
        """
        if self.model_info:
            return self.model_info.dimension

        # Auto-detect dimension
        if EmbeddingModelManager._model is None:
            self._load_model()

        if self.model_name == "text-embedding-3-small":
            return 1536

        # Test with SentenceTransformer
        test_embedding = EmbeddingModelManager._model.encode("test", convert_to_numpy=True)
        return len(test_embedding)

    def encode(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        show_progress_bar: bool = False,
    ) -> List[List[float]]:
        """
        Encode texts to embeddings.

        Args:
            texts: List of texts to encode
            batch_size: Batch size (None = use default)
            show_progress_bar: Show progress bar

        Returns:
            List of embeddings
        """
        if not texts:
            return []

        batch_size = batch_size or self.batch_size

        if EmbeddingModelManager._model is None:
            self._load_model()

        if self.model_name == "text-embedding-3-small":
            # OpenAI embedding
            embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                response = openai.Embedding.create(
                    input=batch,
                    model=self.model_name
                )
                batch_embeddings = [item["embedding"] for item in response["data"]]
                embeddings.extend(batch_embeddings)

            return embeddings

        else:
            # SentenceTransformers
            embeddings = EmbeddingModelManager._model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=show_progress_bar,
                normalize_embeddings=self.normalize,
                convert_to_numpy=True,
            )

            return embeddings.tolist()

    async def encode_async(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
    ) -> List[List[float]]:
        """
        Encode texts asynchronously.

        Args:
            texts: List of texts to encode
            batch_size: Batch size

        Returns:
            List of embeddings
        """
        import asyncio

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.encode(texts, batch_size)
        )

    def encode_single(self, text: str) -> List[float]:
        """
        Encode single text.

        Args:
            text: Text to encode

        Returns:
            Embedding vector
        """
        return self.encode([text])[0]

    async def encode_single_async(self, text: str) -> List[float]:
        """
        Encode single text asynchronously.

        Args:
            text: Text to encode

        Returns:
            Embedding vector
        """
        embeddings = await self.encode_async([text])
        return embeddings[0]

    @staticmethod
    def list_models() -> Dict[str, EmbeddingModelInfo]:
        """List all supported models."""
        return EMBEDDING_MODELS

    @staticmethod
    def get_model_info(model_name: str) -> Optional[EmbeddingModelInfo]:
        """Get information about a specific model."""
        return EMBEDDING_MODELS.get(model_name)


# Convenience function
def get_embedding_manager(
    model_name: Optional[str] = None,
    device: str = "cpu",
    normalize: bool = True,
    batch_size: int = 32,
) -> EmbeddingModelManager:
    """
    Get embedding model manager instance.

    Args:
        model_name: Model name (None = use config)
        device: Device to use
        normalize: Normalize embeddings
        batch_size: Batch size

    Returns:
        EmbeddingModelManager instance
    """
    return EmbeddingModelManager.get_instance(model_name, device, normalize, batch_size)
