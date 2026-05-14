#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Retriever Module

Handles query embedding, similarity search (FAISS/Pinecone), and context building
for retrieval-augmented generation.
"""

import logging
from typing import List, Optional, Any

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


def retrieve_chunks(
    query: str,
    model: SentenceTransformer,
    index: Any,
    all_chunks: Optional[List[str]] = None,
    k: int = 5,
    namespace: Optional[str] = None,
    use_pinecone: bool = True
) -> List[str]:
    """
    Retrieve the top-k most relevant text chunks for a given query.
    
    Args:
        query (str): Search query
        model (SentenceTransformer): Embedding model for query encoding
        index: FAISS or Pinecone index
        all_chunks (Optional[List[str]]): List of all chunks (required for FAISS)
        k (int): Number of chunks to retrieve
        namespace (Optional[str]): Pinecone namespace to query (Pinecone only)
        use_pinecone (bool): Whether to use Pinecone (True) or FAISS (False)
    
    Returns:
        List[str]: List of retrieved chunk texts
    """
    logger.info(f"Retrieving {k} chunks for query: '{query}'...")
    
    # Generate query embedding
    query_embedding = model.encode([query])
    
    if use_pinecone:
        # Pinecone retrieval
        query_vector = query_embedding.tolist()[0] if isinstance(query_embedding, np.ndarray) else query_embedding[0]
        
        response = index.query(
            vector=query_vector,
            top_k=k,
            include_metadata=True,
            namespace=namespace if namespace else ''
        )
        
        retrieved_chunks = []
        for match in response['matches']:
            if 'metadata' in match and 'text' in match['metadata']:
                retrieved_chunks.append(match['metadata']['text'])
            else:
                logger.warning(f"Match found without 'text' metadata: {match.get('id')}")
        
        logger.info(f"Retrieved {len(retrieved_chunks)} chunks from Pinecone.")
        
    else:
        # FAISS retrieval
        if all_chunks is None:
            raise ValueError("all_chunks must be provided for FAISS retrieval")
        
        query_embedding = np.array(query_embedding).astype('float32')
        
        # Perform similarity search
        distances, indices = index.search(query_embedding, k)
        
        # Retrieve chunks using indices
        retrieved_chunks = [all_chunks[idx] for idx in indices[0]]
        
        logger.info(f"Retrieved {len(retrieved_chunks)} chunks from FAISS.")
    
    return retrieved_chunks


def retrieve_similar_documents(
    text_to_compare: str,
    model: SentenceTransformer,
    index: Any,
    k: int = 5,
    namespace: str = ''
) -> List[str]:
    """
    Retrieve similar documents from the main dataset based on text similarity.
    
    Args:
        text_to_compare (str): Text to find similar documents for
        model (SentenceTransformer): Embedding model
        index: Pinecone index
        k (int): Number of similar documents to retrieve
        namespace (str): Pinecone namespace to query
    
    Returns:
        List[str]: List of similar document chunks
    """
    logger.info(f"Retrieving {k} similar documents for text: '{text_to_compare[:100]}...'")
    
    # Generate embedding for the text
    text_embedding = model.encode([text_to_compare]).tolist()[0]
    
    # Query Pinecone
    response = index.query(
        vector=text_embedding,
        top_k=k,
        include_metadata=True,
        namespace=namespace
    )
    
    # Extract chunk texts
    similar_chunks = []
    for match in response['matches']:
        if 'metadata' in match and 'text' in match['metadata']:
            similar_chunks.append(match['metadata']['text'])
        else:
            logger.warning(f"Similar match found without 'text' metadata: {match.get('id')}")
    
    logger.info(f"Successfully retrieved {len(similar_chunks)} similar documents.")
    return similar_chunks


def build_grounded_context(retrieved_chunks: List[str], query: str) -> str:
    """
    Combine retrieved chunks and query into a single formatted context string.
    
    Args:
        retrieved_chunks (List[str]): List of retrieved text chunks
        query (str): User query
    
    Returns:
        str: Formatted grounded context
    """
    logger.info("Building grounded context...")
    combined_chunks = " ".join(retrieved_chunks)
    grounded_context = f"Context (retrieved legal text): {combined_chunks} Query: {query}"
    logger.info("Grounded context built.")
    return grounded_context
