import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.web_search import create_web_search_tool

def test_search():
    load_dotenv()
    print(f"TAVILY_API_KEY in env: {os.getenv('TAVILY_API_KEY')}")
    
    search_tool = create_web_search_tool()
    print(f"Using provider: {search_tool.__class__.__name__}")
    
    query = "similar cases to landmark indian supreme court judgments"
    print(f"Searching for: '{query}'")
    
    results = search_tool.search(query, max_results=3)
    
    if not results:
        print("FAIL: No results returned.")
    else:
        print(f"SUCCESS: Found {len(results)} results.")
        for i, res in enumerate(results):
            print(f"[{i+1}] {res.title}")
            print(f"    URL: {res.url}")
            print(f"    Snippet: {res.snippet[:100]}...")

if __name__ == "__main__":
    test_search()
