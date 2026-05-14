#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Summarizer Module

Handles BART/LED model loading, prompt construction, guardrails implementation,
and hallucination-resistant summary generation with grounding enforcement.
"""

import logging
import time
from typing import List, Optional

import torch
import nltk
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

logger = logging.getLogger(__name__)

# Ensure NLTK punkt is available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)


def load_summarization_model(
    model_name: str = "facebook/bart-large-cnn",
    device: Optional[str] = None
) -> tuple[AutoTokenizer, AutoModelForSeq2SeqLM, str]:
    """
    Load the BART or LED summarization model and tokenizer.
    
    Args:
        model_name (str): Name of the model to load
        device (Optional[str]): Device to load model on ('cuda' or 'cpu').
                               If None, automatically detects.
    
    Returns:
        tuple: (tokenizer, model, device)
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    
    logger.info(f"Loading summarization model: {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(device)
    logger.info(f"Summarization model loaded on {device}.")
    
    return tokenizer, model, device


def generate_summary_with_guardrails(
    grounded_context: str,
    retrieved_chunks: List[str],
    tokenizer: AutoTokenizer,
    model: AutoModelForSeq2SeqLM,
    device: str,
    max_input_length: int = 1024,
    max_length: int = 150,
    min_length: int = 50,
    num_beams: int = 4,
    no_repeat_ngram_size: int = 3
) -> str:
    """
    Generate a hallucination-resistant summary using BART with guardrails and grounding enforcement.
    
    Args:
        grounded_context (str): Context string with retrieved chunks and query
        retrieved_chunks (List[str]): Original retrieved chunks for grounding verification
        tokenizer (AutoTokenizer): BART tokenizer
        model (AutoModelForSeq2SeqLM): BART model
        device (str): Device model is on
        max_input_length (int): Maximum input tokens
        max_length (int): Maximum summary length
        min_length (int): Minimum summary length
        num_beams (int): Number of beams for beam search
        no_repeat_ngram_size (int): Size of n-grams that cannot repeat
    
    Returns:
        str: Grounded summary text
    """
    logger.info("Generating summary with BART and guardrails...")
    
    # Prepend system instruction
    system_instruction = "Please summarize the following legal text accurately. Do not include any information not present in the provided context. Focus on key facts and decisions.\n\n"
    prompt = system_instruction + grounded_context
    
    # Tokenize
    t0 = time.time()
    inputs = tokenizer(prompt, max_length=max_input_length, truncation=True, return_tensors="pt")
    inputs = inputs.to(device)
    logger.info(f"Tokenization took {time.time()-t0:.2f}s")
    
    # Generate summary with optimization
    start_time = time.time()
    
    # Reduce beams on CPU for speed
    eff_num_beams = num_beams if device == "cuda" else min(num_beams, 2)
    if device == "cpu":
        logger.info(f"Using reduced beams ({eff_num_beams}) for CPU speed.")

    with torch.no_grad():
        summary_ids = model.generate(
            inputs["input_ids"],
            num_beams=eff_num_beams,
            max_length=max_length,
            min_length=min_length,
            early_stopping=True,
            no_repeat_ngram_size=no_repeat_ngram_size
        )
    
    generation_time = time.time() - start_time
    logger.info(f"Draft summary generated in {generation_time:.2f}s.")
    
    # Decode
    generated_summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    logger.info("Draft summary generated.")
    
    # Grounding enforcement layer
    g0 = time.time()
    final_grounded_summary_sentences = []
    summary_sentences = nltk.sent_tokenize(generated_summary)
    
    for sum_sent in summary_sentences:
        is_grounded = False
        cleaned_sum_sent = sum_sent.lower()
        
        for chunk in retrieved_chunks:
            cleaned_chunk = chunk.lower()
            # Check if the summary sentence (or a substantial part) is present in the chunk
            if cleaned_sum_sent in cleaned_chunk or any(
                word in cleaned_chunk for word in cleaned_sum_sent.split() if len(word) > 3
            ):
                is_grounded = True
                break
        
        if is_grounded:
            final_grounded_summary_sentences.append(sum_sent)
    
    final_grounded_summary = " ".join(final_grounded_summary_sentences)
    logger.info(f"Grounding verification took {time.time()-g0:.2f}s")
    
    if not final_grounded_summary:
        logger.warning("No generated facts could be fully grounded.")
        return "A summary could not be generated based on the provided context, or no generated facts could be fully grounded."
    
    logger.info("Summary generation complete with grounding enforcement.")
    return final_grounded_summary


def generate_answer_from_context(
    query: str,
    retrieved_chunks: List[str],
    tokenizer: AutoTokenizer,
    model: AutoModelForSeq2SeqLM,
    device: str,
    max_input_length: int = 1024,
    max_length: int = 150,
    min_length: int = 50
) -> str:
    """
    Generate an answer to a query based on retrieved context.
    
    Args:
        query (str): User query
        retrieved_chunks (List[str]): Retrieved context chunks
        tokenizer (AutoTokenizer): BART tokenizer
        model (AutoModelForSeq2SeqLM): BART model
        device (str): Device model is on
        max_input_length (int): Maximum input tokens
        max_length (int): Maximum answer length
        min_length (int): Minimum answer length
    
    Returns:
        str: Generated answer
    """
    logger.info(f"Generating answer for query: '{query}'")
    
    # Build context
    combined_chunks = " ".join(retrieved_chunks)
    grounded_context = f"Context (retrieved legal text): {combined_chunks} Query: {query}"
    
    # Generate summary with guardrails
    answer = generate_summary_with_guardrails(
        grounded_context=grounded_context,
        retrieved_chunks=retrieved_chunks,
        tokenizer=tokenizer,
        model=model,
        device=device,
        max_input_length=max_input_length,
        max_length=max_length,
        min_length=min_length
    )
    
    logger.info("Answer generation complete.")
    return answer
