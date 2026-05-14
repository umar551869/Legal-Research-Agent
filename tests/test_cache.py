import pytest
from app.services.cache import ResearchCache

def test_cache_set_get():
    cache = ResearchCache(ttl_minutes=1)
    query = "test query"
    scope = "HYBRID"
    data = {"result": "success"}
    
    cache.set(query, scope, data)
    assert cache.get(query, scope) == data

def test_cache_expiry():
    # Use a very small TTL or mock datetime
    import time
    from datetime import datetime, timedelta
    
    cache = ResearchCache(ttl_minutes=-1) # Already expired
    query = "expired query"
    scope = "HYBRID"
    data = {"result": "expired"}
    
    cache.set(query, scope, data)
    assert cache.get(query, scope) is None

def test_cache_key_uniqueness():
    cache = ResearchCache()
    cache.set("query 1", "HYBRID", "data 1")
    cache.set("query 2", "HYBRID", "data 2")
    
    assert cache.get("query 1", "HYBRID") == "data 1"
    assert cache.get("query 2", "HYBRID") == "data 2"
