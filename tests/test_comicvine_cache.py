"""
Tests for comicvine_cache.py
"""
import time
from comicvine_cache import ComicVineCache


def test_upsert_and_get():
    cache = ComicVineCache(db_path=":memory:", ttl_seconds=60)
    cache.upsert_issue("1", {"a": 1})
    row = cache.get_issue("1")
    assert row is not None
    assert row["data"]["a"] == 1
    cache.close()


def test_fetch_or_get_with_fetcher():
    cache = ComicVineCache(db_path=":memory:", ttl_seconds=60)

    def fetcher(i):
        return {"id": i, "title": "Fetched"}

    data = cache.fetch_or_get("2", fetcher)
    assert data["title"] == "Fetched"

    # second call should hit cache (not call fetcher again); simulate by using a fetcher that would raise
    def bad_fetcher(i):
        raise RuntimeError("no network")

    data2 = cache.fetch_or_get("2", bad_fetcher)
    assert data2["title"] == "Fetched"
    cache.close()


def test_ttl_expiration():
    cache = ComicVineCache(db_path=":memory:", ttl_seconds=1)

    def fetcher(i):
        return {"id": i, "title": "Fresh"}

    cache.fetch_or_get("3", fetcher)
    time.sleep(2)

    # After TTL, fetcher should be called again; create a fetcher that returns different data
    def fetcher2(i):
        return {"id": i, "title": "Refreshed"}

    data = cache.fetch_or_get("3", fetcher2)
    assert data["title"] == "Refreshed"
    cache.close()
