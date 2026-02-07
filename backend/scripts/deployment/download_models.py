import logging
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_models():
    """
    Pre-download models for Docker image to avoid runtime downloads.
    """
    model_name = 'all-MiniLM-L6-v2'
    logger.info(f"Downloading model: {model_name}")
    
    # This will download to the default cache folder (usually ~/.cache/huggingface/hub)
    # or SENTENCE_TRANSFORMERS_HOME if set.
    model = SentenceTransformer(model_name)
    logger.info("Model download complete.")

    # Optional: Test load
    embeddings = model.encode(["Test sentence"])
    logger.info(f"Test encoding shape: {embeddings.shape}")

if __name__ == "__main__":
    download_models()
