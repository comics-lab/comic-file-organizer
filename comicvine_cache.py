"""
Simple SQLite-backed cache for ComicVine issue metadata.

Usage:
    cache = ComicVineCache(db_path="./comicvine_cache.db", ttl_seconds=86400)
    data = cache.fetch_or_get(issue_id, fetcher_callable)

The fetcher_callable should be a function taking issue_id and returning a dict (the data to cache).
"""
import sqlite3
import json
import time
from typing import Optional, Callable, Dict, Any
from pathlib import Path


class ComicVineCache:
    def __init__(self, db_path: str = ":memory:", ttl_seconds: int = 86400):
        self.db_path = db_path
        self.ttl = int(ttl_seconds)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS issues (
                issue_id TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_updated_at ON issues(updated_at)")
        self._conn.commit()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def upsert_issue(self, issue_id: str, data: Dict[str, Any]) -> None:
        now = int(time.time())
        cur = self._conn.cursor()
        cur.execute(
            "REPLACE INTO issues (issue_id, data_json, updated_at) VALUES (?, ?, ?)",
            (issue_id, json.dumps(data), now),
        )
        self._conn.commit()

    def get_issue(self, issue_id: str) -> Optional[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute("SELECT data_json, updated_at FROM issues WHERE issue_id = ?", (issue_id,))
        row = cur.fetchone()
        if not row:
            return None
        data_json, updated_at = row
        try:
            data = json.loads(data_json)
        except Exception:
            return None
        return {"data": data, "updated_at": int(updated_at)}

    def is_stale(self, updated_at: int) -> bool:
        now = int(time.time())
        return (now - int(updated_at)) > self.ttl

    def fetch_or_get(self, issue_id: str, fetcher: Callable[[str], Dict[str, Any]]) -> Dict[str, Any]:
        """Return data for issue_id: try cache, if missing or stale call fetcher(issue_id), store and return result."""
        row = self.get_issue(issue_id)
        if row:
            if not self.is_stale(row["updated_at"]):
                return row["data"]

        # Need to fetch from upstream
        data = fetcher(issue_id)
        # If fetcher returns None or empty, don't overwrite a fresher existing row; return what we have
        if data is None:
            if row:
                return row["data"]
            raise RuntimeError(f"Fetcher did not return data for {issue_id}")

        self.upsert_issue(issue_id, data)
        return data


def _example_fetcher(issue_id: str) -> Dict[str, Any]:
    # Placeholder example: replace with real ComicVine API fetch
    return {"id": issue_id, "title": f"Issue {issue_id}", "fetched_at": int(time.time())}


if __name__ == "__main__":
    cache = ComicVineCache(db_path=":memory:")
    print(cache.fetch_or_get("12345", _example_fetcher))
    cache.close()
