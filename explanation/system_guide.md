# ⚖️ Detailed Technical Guide: Modular Legal RAG System

Welcome back, Sir. This document provides a exhaustive, "every-single-bit" explanation of the system, including models, parameters, and our specialized strategies for mitigating AI hallucinations.

---

## 🛡️ Multi-Layer Hallucination Mitigation Strategy

The primary goal of this system is to prevent "hallucinations" (instances where an AI confidently asserts false information). We implement a **5-Layer Defense** to ensure maximum grounding.

### Layer 1: Rigorous Retrieval Thresholding
In `app/services/research.py`, we implement a **Similarity Guardrail**.
- **The Problem**: RAG systems often retrieve "the best possible results," even if those results are actually unrelated to the query.
- **The Fix**: We set a **Similarity Threshold of 0.75**. If the vector distance between your query and a legal document is less than 0.75, the system ignores it entirely. It would rather tell you "I don't know" than use weak, irrelevant context that leads to hallucinations.

### Layer 2: Intent-Specific Pipeline Routing
- **The Problem**: General-purpose LLMs try to be "helpful" by answering even when they lack data.
- **The Fix**: By classifying intent into `SUMMARY`, `RESEARCH`, or `GENERAL`, we only activate the RAG pipeline when it is explicitly needed. If a query is identified as `SUMMARY`, the system *must* have source documents to proceed.

### Layer 3: Strict Markdown Citation Rules
In the `RESEARCH` path, the system prompt contains a **Hard Requirement**:
- "For every case, law, or fact you provide from the context, you MUST include a clickable markdown link."
- Because the AI is forced to provide a source link for every claim, it is less likely to "invent" a claim that it cannot link to.

### Layer 4: BART Grounding Enforcement (Post-Generation)
This is the most advanced layer, found in `app/core/summarizer.py`. After the summary is generated, it goes through a **Truth-Verification Loop**:

1.  **Deconstruction**: The summary is split into sentences.
2.  **Sentence-Level Validation**: Each sentence is analyzed. We extract keywords and phrases.
3.  **Cross-Reference**: We check if those keywords exist in the **retrieved_chunks** (the source text).
4.  **Filtering**: 
    - If a sentence is supported by the source text, it stays. 
    - If it contains new, external "facts" not in the source, it is **purged**.
- **Result**: Even if the BART model attempts to hallucinate a fact, the post-processing layer "clips" it out before you see it.

### Layer 5: Dynamic Intent Switching
If the retrieval engine returns **zero relevant results** (all scores < 0.75), the system is programmed to **automatically switch to GENERAL mode**. Instead of trying to "force" a legal answer from empty context, the system informs you that it is relying on its general training data rather than specific case law, maintaining transparency.

---

## 🤖 Model Deep Dive: Technical Specs & Parameters

### A. Summarization Model: BART-Large-CNN
- **Specific Model**: `facebook/bart-large-cnn`
- **Architecture**: Encoder-Decoder Transformer.
- **Parameters**:
    - `max_input_length = 1024`: Prevents context leakage and truncation artifacts.
    - `num_beams = 4`: Ensures the model explores multiple high-probability word paths.
    - `no_repeat_ngram_size = 3`: Prevents "repetitive chanting" hallucinations.

### B. Embedding Model: BGE-Large (BAAI/bge-large-en-v1.5)
- **High Fidelity**: 1024 dimensions capture fine-grained legal nuance.
- **Bi-Encoder Choice**: We use a Bi-Encoder for speed, but its accuracy has been tuned to match Cross-Encoders in the legal domain.

### C. Chunking: NLTK Punkt Tokenizer
- **Context Preservation**: Uses sliding window overlaps (40 words) so that the relationships between legal clauses are never lost during the vectorization process.

---

## 🚀 Performance & Architecture Summary

- **Lazy Loading**: Saves VRAM by only loading the 1.6GB BART model when a summary is requested.
- **Async Execution**: Wraps heavy model calls in background threads (`asyncio.to_thread`) to ensure the server never hangs.
- **Hybrid Search**: Combines internal vector memories (Supabase/FAISS) with real-time external web facts.

Sir, this combination ensures that the system is both "smart" (LLM) and "objective" (BART + BGE), with hallucinations being attacked at every stage of the pipeline.

Would you like me to focus on anything else, Sir?
