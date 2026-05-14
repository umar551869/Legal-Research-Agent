#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Search Module (Robust Version + Tavily Support)

Provides web search functionality using:
1. Tavily API (Industry Standard, Best for RAG) - Requires API Key
2. DuckDuckGo (Manual Scrape) - Free fallback
"""

import logging
import requests
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import urllib.parse
import os

from langchain_core.documents import Document
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class SearchResult:
    """Structured search result from any provider."""
    title: str
    url: str
    snippet: str
    score: Optional[float] = None  # Relevance score if available

    def to_document(self) -> Document:
        """Convert to LangChain Document for RAG pipeline."""
        return Document(
            page_content=f"{self.title}\n\n{self.snippet}",
            metadata={
                "source": self.url,
                "title": self.title,
                "type": "web_search"
            }
        )


# ============================================================================
# ABSTRACT BASE CLASS
# ============================================================================

class BaseWebSearch(ABC):
    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        pass

    def search_as_documents(self, query: str, max_results: int = 5) -> List[Document]:
        results = self.search(query, max_results)
        documents = [result.to_document() for result in results]
        logger.info(f"Converted {len(documents)} search results to Documents")
        return documents


# ============================================================================
# TAVILY IMPLEMENTATION (PAID/FREE KEY) - RECOMMENDED
# ============================================================================

class TavilySearch(BaseWebSearch):
    """
    Tavily search implementation (API key required).
    Best for RAG as it returns optimized context.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        # We use direct HTTP to avoid extra dependency 'tavily-python' if not installed
        # but typical usage is the library. Let's use requests for zero-dep.
        self.endpoint = "https://api.tavily.com/search"

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        logger.info(f"Tavily search: '{query}' (max_results={max_results})")
        
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
        }
        
        try:
            resp = requests.post(self.endpoint, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            results = []
            for item in data.get('results', []):
                results.append(SearchResult(
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    snippet=item.get('content', ''),
                    score=item.get('score', 0.0)
                ))
            
            logger.info(f"Retrieved {len(results)} results from Tavily")
            return results
            
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return []


# ============================================================================
# ROBUST DUCKDUCKGO IMPLEMENTATION (HTML SCRAPE) - FALLBACK
# ============================================================================

class DuckDuckGoSearch(BaseWebSearch):
    """
    Robust DuckDuckGo search using direct HTML POST requests.
    """
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://duckduckgo.com/"
        })

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        logger.info(f"DuckDuckGo (Manual Scrape): '{query}' (max_results={max_results})")
        url = "https://html.duckduckgo.com/html/"
        payload = {'q': query}
        
        try:
            resp = self.session.post(url, data=payload, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            results = []
            
            for result_div in soup.select('.result'):
                if len(results) >= max_results:
                    break
                
                title_tag = result_div.select_one('.result__a')
                if not title_tag: continue
                
                title = title_tag.get_text(strip=True)
                raw_url = title_tag.get('href', '')
                
                if "duckduckgo.com/l/?" in raw_url:
                    parsed = urllib.parse.urlparse(raw_url)
                    qs = urllib.parse.parse_qs(parsed.query)
                    final_url = qs['uddg'][0] if 'uddg' in qs else raw_url
                else:
                    final_url = raw_url

                snippet_tag = result_div.select_one('.result__snippet')
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                
                results.append(SearchResult(title=title, url=final_url, snippet=snippet))
            
            return results

        except Exception as e:
            logger.error(f"Manual DDG search failed: {e}")
            return []


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_web_search_tool(
    provider: str = None, # Auto-detect
    api_key: Optional[str] = None
) -> BaseWebSearch:
    
    # Priority 1: Explicitly provided
    if provider == "tavily" and api_key:
        return TavilySearch(api_key)
    
    # Priority 2: Environment Variable
    env_key = os.getenv("TAVILY_API_KEY")
    if env_key:
        logger.info("Using Tavily Search (Key found in env)")
        return TavilySearch(env_key)
        
    # Priority 3: Fallback
    logger.info("Using DuckDuckGo Search (Fallback)")
    return DuckDuckGoSearch()
