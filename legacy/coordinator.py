import logging
import json
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv

load_dotenv()

from ollama_utils import OllamaClient
from web_search import create_web_search_tool, SearchResult
from embedding_store import initialize_embedding_model, create_or_load_faiss_index, add_embeddings_to_faiss, embed_texts
from ingestion import chunk_text
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LegalResearchCoordinator:
    def __init__(self):
        self.ollama = OllamaClient()
        self.web_search_provider = create_web_search_tool()
            
        self.embedding_model = initialize_embedding_model()
        self.uploaded_doc_index = None
        self.uploaded_doc_chunks = []
        self.uploaded_doc_name = None
        
        # Placeholder for internal DB - in a real app this might connect to Pinecone
        # For now we will rely on external or uploaded, or a local FAISS if present
        self.internal_index = None 
        # self.internal_index = create_or_load_faiss_index(768, "internal_db.index") 

    def process_uploaded_document(self, file_name: str, file_text: str):
        """
        Ingest and index a user-uploaded document on the fly.
        """
        logger.info(f"Processing uploaded document: {file_name}")
        self.uploaded_doc_name = file_name
        self.uploaded_doc_chunks = chunk_text(file_text)
        
        if not self.uploaded_doc_chunks:
            logger.warning("No chunks created from document.")
            return

        # Create ephemeral FAISS index
        embeddings = embed_texts(self.uploaded_doc_chunks, self.embedding_model)
        
        # Dimension depends on model (all-mpnet-base-v2 is 768)
        dim = embeddings.shape[1]
        self.uploaded_doc_index = create_or_load_faiss_index(dim)
        add_embeddings_to_faiss(self.uploaded_doc_index, embeddings)
        logger.info("Document indexed successfully.")

    def classify_query(self, query: str) -> Dict[str, Any]:
        """
        Step 1: Identify the Query Scope using LLM.
        """
        system_prompt = """
        You are a legal research router. Classify the user query into ONE of the following scopes:
        1. "UPLOADED_DOC": Query is explicitly about "this document", "the uploaded file", or specific clauses in it.
        2. "INTERNAL_DB": General legal concepts, standard principles, or case law requests not specific to recent news.
        3. "EXTERNAL_WEB": Queries asking for recent rulings, specific case facts likely online, or "missing precedents".
        4. "HYBRID": Comparisons between uploaded doc and general law.
        
        Return JSON only: {"scope": "...", "reasoning": "..."}
        """
        
        response = self.ollama.generate(query, system=system_prompt, json_mode=True)
        try:
            # Handle potential string output if JSON mode isn't perfect
            res_text = response.get('response', '{}')
            return json.loads(res_text)
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            # Fallback based on keywords
            if "this document" in query.lower() or "uploaded" in query.lower():
                return {"scope": "UPLOADED_DOC"}
            return {"scope": "INTERNAL_DB"}

    def run_query(self, query: str) -> str:
        """
        Main execution flow.
        """
        # Step 1: Classify
        classification = self.classify_query(query)
        scope = classification.get("scope", "INTERNAL_DB")
        logger.info(f"Query Scope Classified: {scope}")
        
        sources_consulted = []
        retrieved_texts = []
        
        # Step 2: Retrieval Routing
        
        # A. Uploaded Doc Search
        if scope in ["UPLOADED_DOC", "HYBRID"] and self.uploaded_doc_index:
            logger.info("Searching uploaded document...")
            query_vec = embed_texts([query], self.embedding_model)[0].reshape(1, -1)
            dist, ind = self.uploaded_doc_index.search(query_vec.astype('float32'), k=3)
            
            for i in ind[0]:
                if i < len(self.uploaded_doc_chunks):
                    chunk = self.uploaded_doc_chunks[i]
                    retrieved_texts.append(f"[Uploaded Doc] {chunk}")
            sources_consulted.append(f"Uploaded Document: {self.uploaded_doc_name}")

        # B. Internal Search (Placeholder logic)
        if scope in ["INTERNAL_DB", "HYBRID"]:
            logger.info("Searching internal database (Simulated)...")
            # In a real scenario, query Pinecone here. 
            # For this demo, we might skip or fallback to Web if internal is empty
            sources_consulted.append("Internal Database (No matches found - Demo Mode)")
        
        # C. External Search
        if scope in ["EXTERNAL_WEB", "HYBRID"] or (scope == "INTERNAL_DB" and not retrieved_texts):
            logger.info("Searching external web...")
            results = self.web_search_provider.search(query, max_results=3)
            for res in results:
                retrieved_texts.append(f"[Web Source: {res.title}] {res.snippet}")
                sources_consulted.append(f"External Web: {res.title} ({res.url})")

        # Step 3: Synthesis
        if not retrieved_texts:
            return "No relevant legal information found in the available sources."
            
        context_str = "\n\n".join(retrieved_texts)
        
        final_system_prompt = """
        You are a strict Legal Research Coordinator. 
        Use the provided CONTEXT to answer the user query.
        
        Mandatory Format:
        
        Query Interpretation
        [Brief restatement]
        
        Sources Consulted
        [List the sources provided in the context metadata]
        
        Retrieved Authorities
        [List distinct cases/docs found in context]
        
        Findings
        [Legal principles/facts strictly from context]
        
        Conclusion
        [Neutral synthesis]
        
        Constraints:
        - NO Hallucination.
        - If context is insufficient, state "Insufficient information".
        - NO legal advice.
        """
        
        final_prompt = f"User Query: {query}\n\nContext:\n{context_str}"
        
        logger.info("Generating final response...")
        resp = self.ollama.generate(final_prompt, system=final_system_prompt)
        return resp.get("response", "Error generating response.")

if __name__ == "__main__":
    # Test block
    coord = LegalResearchCoordinator()
    print("Coordinator initialized.")
