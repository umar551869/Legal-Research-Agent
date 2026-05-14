import asyncio
from pinecone import Pinecone
from app.core.embedding_store import initialize_embedding_model, embed_texts
from app.config import settings

async def main():
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    index = pc.Index(settings.PINECONE_INDEX_NAME)
    
    model = initialize_embedding_model()
    query = "Appeals Nos. 490 and 491 of 1958. Appeals from the judgment and decree dated February 18, 1955"
    query_vec = embed_texts([query], model, show_progress_bar=False)[0]
    
    # Query WITH namespace
    response = index.query(
        vector=query_vec.tolist(),
        top_k=3,
        include_metadata=True,
        namespace=settings.PINECONE_INDEX_NAME
    )
    
    matches = response.get("matches", [])
    print(f"Matches found: {len(matches)}")
    for i, match in enumerate(matches):
        meta = match.get("metadata", {})
        print(f"\n--- Match {i+1} (score: {match.get('score', 'N/A')}) ---")
        print(f"Metadata keys: {list(meta.keys())}")
        for key, value in meta.items():
            val_str = str(value)
            print(f"  {key}: {val_str[:300]}")

if __name__ == "__main__":
    asyncio.run(main())
