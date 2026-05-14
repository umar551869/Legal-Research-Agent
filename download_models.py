import os
import logging
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from sentence_transformers import SentenceTransformer
import nltk

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download():
    # 1. BART Summarizer
    model_name = "facebook/bart-large-cnn"
    logger.info(f"Downloading/Caching BART model: {model_name}...")
    AutoTokenizer.from_pretrained(model_name)
    AutoModelForSeq2SeqLM.from_pretrained(model_name)
    logger.info("BART model cached.")

    # 2. BGE Embeddings
    embed_model = "BAAI/bge-large-en-v1.5"
    logger.info(f"Downloading/Caching Embedding model: {embed_model}...")
    SentenceTransformer(embed_model)
    logger.info("Embedding model cached.")

    # 3. NLTK Data
    logger.info("Downloading NLTK punkt...")
    nltk.download('punkt', quiet=False)
    logger.info("NLTK data cached.")

    logger.info("All models and data have been pre-downloaded and cached successfully!")

if __name__ == "__main__":
    download()
