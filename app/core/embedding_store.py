#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Embedding Store Module

Handles embedding model initialization, embedding generation, and vector database operations
(both FAISS and Pinecone). Manages vector upserts and namespace operations.
"""

import os
import logging
from typing import List, Dict, Any, Optional

import numpy as np
import torch
import faiss
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


def initialize_embedding_model(
    model_name: str = 'BAAI/bge-large-en-v1.5',
    device: Optional[str] = None
) -> SentenceTransformer:
    """
    Initialize the SentenceTransformer embedding model.
    
    Args:
        model_name (str): Name of the SentenceTransformer model to load
        device (Optional[str]): Device to load model on ('cuda' or 'cpu'). 
                               If None, automatically detects.
    
    Returns:
        SentenceTransformer: Loaded embedding model
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    
    logger.info(f"Loading embedding model: {model_name} on {device}...")
    model = SentenceTransformer(model_name, device=device)
    logger.info("Embedding model loaded successfully.")
    
    return model


def embed_texts(
    texts: List[str],
    model: SentenceTransformer,
    convert_to_numpy: bool = True,
    show_progress_bar: bool = True
) -> np.ndarray:
    """
    Generate embeddings for a list of texts.
    
    Args:
        texts (List[str]): List of text strings to embed
        model (SentenceTransformer): Embedding model to use
        convert_to_numpy (bool): Whether to convert to numpy array
        show_progress_bar (bool): Whether to show progress bar
    
    Returns:
        np.ndarray: Array of embeddings
    """
    logger.info(f"Generating embeddings for {len(texts)} texts...")
    embeddings = model.encode(
        texts,
        convert_to_numpy=convert_to_numpy,
        show_progress_bar=show_progress_bar
    )
    logger.info(f"Embeddings generated. Shape: {embeddings.shape}")
    return embeddings


def create_or_load_faiss_index(
    embedding_dim: int,
    index_path: Optional[str] = None
) -> faiss.IndexFlatL2:
    """
    Create a new FAISS index or load an existing one.
    
    Args:
        embedding_dim (int): Dimension of the embeddings
        index_path (Optional[str]): Path to existing FAISS index file. 
                                    If None, creates new index.
    
    Returns:
        faiss.IndexFlatL2: FAISS index
    """
    if index_path and os.path.exists(index_path):
        logger.info(f"Loading existing FAISS index from {index_path}...")
        index = faiss.read_index(index_path)
        logger.info(f"FAISS index loaded. Total vectors: {index.ntotal}")
    else:
        logger.info(f"Creating new FAISS index with dimension {embedding_dim}...")
        index = faiss.IndexFlatL2(embedding_dim)
        logger.info("FAISS index created.")
    
    return index


def add_embeddings_to_faiss(
    index: faiss.IndexFlatL2,
    embeddings: np.ndarray,
    save_path: Optional[str] = None
) -> None:
    """
    Add embeddings to FAISS index and optionally save.
    
    Args:
        index (faiss.IndexFlatL2): FAISS index to add embeddings to
        embeddings (np.ndarray): Embeddings to add
        save_path (Optional[str]): Path to save the index after adding
    """
    logger.info(f"Adding {len(embeddings)} embeddings to FAISS index...")
    index.add(embeddings.astype('float32'))
    logger.info(f"Embeddings added. Total vectors in index: {index.ntotal}")
    
    if save_path:
        logger.info(f"Saving FAISS index to {save_path}...")
        faiss.write_index(index, save_path)
        logger.info("FAISS index saved.")


def create_or_connect_pinecone_index(
    api_key: str,
    index_name: str,
    embedding_dim: int,
    metric: str = "cosine",
    cloud: str = "aws",
    region: str = "us-east-1"
) -> Any:
    """
    Stub implementation: Pinecone support is disabled in this build.

    This project currently uses FAISS and Supabase for vector search.
    If you need Pinecone integration, you can re-enable it by:
    - Adding the official `pinecone` package to requirements, and
    - Implementing this function to create/connect the index.
    """
    raise RuntimeError(
        "Pinecone integration is disabled in this build. "
        "Re-enable it by adding the official `pinecone` client and updating "
        "`create_or_connect_pinecone_index` if you need Pinecone support."
    )


def upsert_documents(
    index: Any,
    chunk_texts: List[str],
    chunk_embeddings: np.ndarray,
    document_ids: List[str],
    namespace: str = "",
    batch_size: int = 100,
    metadata_text_limit: int = 1000
) -> Dict[str, Any]:
    """
    Upsert document chunks with embeddings to Pinecone index.
    
    IMPORTANT: This function APPENDS new vectors to the existing namespace.
    It does NOT replace or delete existing data. All previous vectors remain intact.
    
    The upsert operation:
    - Adds new vectors with unique IDs
    - Updates vectors if the same ID already exists (rare, as we use UUID-based IDs)
    - Preserves all other existing vectors in the namespace
    
    Args:
        index: Pinecone index object
        chunk_texts (List[str]): List of text chunks
        chunk_embeddings (np.ndarray): Embeddings for the chunks
        document_ids (List[str]): Document IDs for each chunk
        namespace (str): Pinecone namespace to upsert into (default: "" for default namespace)
        batch_size (int): Number of vectors to upsert per batch
        metadata_text_limit (int): Maximum characters for metadata text field
    
    Returns:
        Dict[str, Any]: Statistics about the upsert operation containing:
            - vectors_before: Number of vectors before upsert
            - vectors_after: Number of vectors after upsert
            - vectors_added: Number of new vectors added
            - namespace: The namespace that was updated
    """
    namespace_display = namespace if namespace else "default"
    logger.info(f"="*60)
    logger.info(f"APPEND-ONLY UPSERT TO NAMESPACE: '{namespace_display}'")
    logger.info(f"="*60)
    
    # Get statistics BEFORE upsert
    logger.info("Fetching index statistics before upsert...")
    stats_before = index.describe_index_stats()
    namespace_key = namespace if namespace else '__default__'
    vectors_before = stats_before.get('namespaces', {}).get(namespace_key, {}).get('vector_count', 0)
    
    logger.info(f"Vectors in namespace '{namespace_display}' BEFORE upsert: {vectors_before}")
    logger.info(f"Preparing to ADD {len(chunk_texts)} new vectors (append-only)...")
    
    # Prepare vectors for upsert
    pinecone_vectors = []
    for chunk_idx, (chunk_text, doc_id) in enumerate(zip(chunk_texts, document_ids)):
        vector_id = f"{doc_id}-{chunk_idx}"
        
        metadata = {
            "text": chunk_text[:metadata_text_limit],
            "document_id": doc_id
        }
        
        pinecone_vectors.append({
            "id": vector_id,
            "values": chunk_embeddings[chunk_idx].tolist(),
            "metadata": metadata
        })
    
    logger.info(f"Prepared {len(pinecone_vectors)} vectors for append operation.")
    
    # Batch upsert (APPEND operation)
    total_vectors = len(pinecone_vectors)
    logger.info(f"Appending {total_vectors} vectors in batches of {batch_size}...")
    
    successful_batches = 0
    failed_batches = 0
    
    for i in range(0, total_vectors, batch_size):
        batch = pinecone_vectors[i:i + batch_size]
        try:
            # UPSERT = INSERT new vectors OR UPDATE if ID exists
            # Since we use unique IDs (UUID-based), this effectively APPENDS
            index.upsert(vectors=batch, namespace=namespace)
            batch_num = int(i/batch_size) + 1
            total_batches = (total_vectors + batch_size - 1) // batch_size
            logger.info(f"✓ Appended batch {batch_num}/{total_batches} (vectors {i} to {min(i + batch_size, total_vectors) - 1})")
            successful_batches += 1
        except Exception as e:
            logger.error(f"✗ Error appending batch {int(i/batch_size) + 1}: {e}")
            failed_batches += 1
    
    logger.info(f"Batch operation complete: {successful_batches} successful, {failed_batches} failed")
    
    # Get statistics AFTER upsert
    logger.info("Fetching index statistics after upsert...")
    stats_after = index.describe_index_stats()
    vectors_after = stats_after.get('namespaces', {}).get(namespace_key, {}).get('vector_count', 0)
    vectors_added = vectors_after - vectors_before
    
    # Log summary
    logger.info(f"="*60)
    logger.info(f"UPSERT SUMMARY - NAMESPACE: '{namespace_display}'")
    logger.info(f"="*60)
    logger.info(f"Vectors BEFORE: {vectors_before}")
    logger.info(f"Vectors AFTER:  {vectors_after}")
    logger.info(f"Vectors ADDED:  {vectors_added}")
    logger.info(f"Operation:      APPEND (existing data preserved)")
    logger.info(f"="*60)
    
    return {
        "vectors_before": vectors_before,
        "vectors_after": vectors_after,
        "vectors_added": vectors_added,
        "namespace": namespace_display,
        "successful_batches": successful_batches,
        "failed_batches": failed_batches
    }

