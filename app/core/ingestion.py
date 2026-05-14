#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ingestion Module

Handles text preprocessing, cleaning, chunking, and dataset loading.
Provides utilities for preparing raw text data for embedding and storage.
"""

import os
import re
import string
import logging
from typing import List, Optional

import pandas as pd
import nltk

logger = logging.getLogger(__name__)

# Download NLTK data if not already present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    logger.info("Downloading NLTK 'punkt' tokenizer...")
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)


def clean_text(text: str) -> str:
    """
    Clean and normalize text by converting to lowercase and removing punctuation.
    
    Args:
        text (str): Input text to clean
    
    Returns:
        str: Cleaned text
    """
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text


def chunk_text(text: str, chunk_size: int = 250, overlap: int = 40) -> List[str]:
    """
    Split text into chunks of approximately chunk_size words with overlap.
    
    Args:
        text (str): Input text to chunk
        chunk_size (int): Target number of words per chunk
        overlap (int): Number of words to overlap between chunks
    
    Returns:
        List[str]: List of text chunks
    """
    if not text or pd.isna(text):
        return []
    
    sentences = nltk.sent_tokenize(text)
    chunks = []
    current_chunk_sentences = []
    current_chunk_word_count = 0
    
    for sentence in sentences:
        sentence_words = sentence.split()
        sentence_word_count = len(sentence_words)
        
        # If adding the current sentence would exceed chunk_size significantly, finalize current chunk
        if current_chunk_word_count + sentence_word_count > chunk_size and current_chunk_word_count > 0:
            chunks.append(" ".join(current_chunk_sentences))
            
            # Create overlap: take the last 'overlap' words from the current chunk
            overlap_sentences_words = []
            temp_word_count = 0
            # Iterate backward through current_chunk_sentences to get sentences for overlap
            for i in range(len(current_chunk_sentences) - 1, -1, -1):
                s = current_chunk_sentences[i]
                if temp_word_count + len(s.split()) <= overlap:
                    overlap_sentences_words.insert(0, s)  # Prepend to maintain order
                    temp_word_count += len(s.split())
                else:
                    # If adding the whole sentence exceeds overlap, take only necessary words
                    remaining_overlap = overlap - temp_word_count
                    if remaining_overlap > 0:
                        overlap_sentences_words.insert(0, " ".join(s.split()[-remaining_overlap:]))
                    break
            current_chunk_sentences = overlap_sentences_words
            current_chunk_word_count = temp_word_count
        
        current_chunk_sentences.append(sentence)
        current_chunk_word_count += sentence_word_count
    
    if current_chunk_sentences:
        chunks.append(" ".join(current_chunk_sentences))
    
    return chunks


def load_legal_dataset(csv_path: str) -> pd.DataFrame:
    """
    Load legal cases dataset from CSV file.
    
    Args:
        csv_path (str): Path to the CSV file
    
    Returns:
        pd.DataFrame: DataFrame containing legal cases
    """
    logger.info(f"Loading legal cases from {csv_path}...")
    df = pd.read_csv(csv_path)
    logger.info(f"Successfully loaded {len(df)} legal cases.")
    logger.info(f"DataFrame columns: {df.columns.tolist()}")
    return df


def preprocess_documents(
    df: pd.DataFrame,
    text_column: str = 'judgement',
    chunk_size: int = 250,
    overlap: int = 40
) -> tuple[List[str], List[str], List[str]]:
    """
    Preprocess documents from DataFrame: clean, chunk, and prepare for embedding.
    
    Args:
        df (pd.DataFrame): DataFrame containing documents
        text_column (str): Name of column containing text to process
        chunk_size (int): Target words per chunk
        overlap (int): Overlap words between chunks
    
    Returns:
        tuple: (all_chunks, document_ids, cleaned_texts)
            - all_chunks: Flattened list of all text chunks
            - document_ids: Document ID for each chunk
            - cleaned_texts: List of cleaned full texts
    """
    logger.info(f"Preprocessing documents from column '{text_column}'...")
    
    # Add document IDs
    df['document_id'] = df.index.astype(str)
    
    # Clean texts
    logger.info("Cleaning texts...")
    df['cleaned_judgement'] = df[text_column].apply(clean_text)
    
    # Chunk texts
    logger.info("Chunking texts...")
    df['chunks'] = df['cleaned_judgement'].apply(
        lambda x: chunk_text(x, chunk_size=chunk_size, overlap=overlap)
    )
    
    # Flatten chunks and track document IDs
    all_chunks = []
    document_ids = []
    
    for idx, row in df.iterrows():
        doc_id = str(row['document_id'])
        for chunk in row['chunks']:
            all_chunks.append(chunk)
            document_ids.append(doc_id)
    
    logger.info(f"Total chunks created: {len(all_chunks)}")
    logger.info(f"First 3 chunks: {[c[:100] + '...' for c in all_chunks[:3]]}")
    
    cleaned_texts = df['cleaned_judgement'].tolist()
    
    return all_chunks, document_ids, cleaned_texts
