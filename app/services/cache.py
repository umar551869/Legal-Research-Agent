import hashlib
import json
import logging
from typing import Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ResearchCache:
    """
    In-memory cache for research results. 
    In the future, this can be swapped with Redis for distributed environments.
    """
    def __init__(self, ttl_minutes: int = 60):
        self._cache = {}
        self._ttl = timedelta(minutes=ttl_minutes)
        logger.info(f"ResearchCache initialized with TTL: {ttl_minutes} minutes")

    def _generate_key(self, query: str, scope: str) -> str:
        """Create a unique hash for the query and its scope."""
        key_data = f"{query.strip().lower()}:{scope}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(self, query: str, scope: str) -> Optional[Any]:
        """Retrieve a result from cache if it exists and hasn't expired."""
        key = self._generate_key(query, scope)
        if key in self._cache:
            entry = self._cache[key]
            if datetime.now() < entry["expires"]:
                logger.info(f"Cache HIT for: {query[:50]}...")
                return entry["data"]
            else:
                # Cleanup expired entry
                del self._cache[key]
        
        logger.info(f"Cache MISS for: {query[:50]}...")
        return None

    def set(self, query: str, scope: str, data: Any):
        """Store a result in cache."""
        key = self._generate_key(query, scope)
        self._cache[key] = {
            "data": data,
            "expires": datetime.now() + self._ttl
        }
        # Optional: Implement LRU eviction if memory becomes an issue
        if len(self._cache) > 1000:
            # Simple cleanup: remove the first key if cache grows too large
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

research_cache = ResearchCache()
