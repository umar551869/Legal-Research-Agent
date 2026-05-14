import asyncio
import json
from app.services.global_kb import global_kb

async def check():
    results = await global_kb.search("appeal no lxvi of 1949", k=1)
    if results:
        meta = results[0].get("metadata", {})
        print("METADATA_START")
        print(json.dumps(meta, indent=2))
        print("METADATA_END")
    else:
        print("No results found.")

if __name__ == "__main__":
    asyncio.run(check())
