"""
Simple thread-safe caching layer for DataFrame results using SQLite. Kept generic
as it should be reusable across different types of data and providers.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from io import StringIO
from pathlib import Path
from threading import Lock
from typing import Any

import pandas as pd

from financetoolkit.utilities.logger_model import get_logger

logger = get_logger()


class SQLiteCache:
    """Thread-safe SQLite cache for DataFrame API results."""

    def __init__(self, database_location: str) -> None:
        """
        Initializes the SQLiteCache.

        Args:
            database_location (str): Path to the SQLite database file. The parent
                directory is created automatically if it does not already exist.
        """
        self._database_location = database_location
        self._lock = Lock()

        self.initialize_database()

    def initialize_database(self) -> None:
        """
        Create the cache table and index if they do not exist.

        This ensures the underlying SQLite schema required for caching is present
        before any read or write operations are attempted.
        """
        # If the parent folder doesn't exist, create it to avoid SQLite errors.
        # This allows for flexible database locations, including in-memory or
        # on-disk paths.
        Path(self._database_location).parent.mkdir(parents=True, exist_ok=True)

        with self._lock, sqlite3.connect(self._database_location) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key    TEXT PRIMARY KEY,
                    value  TEXT NOT NULL,
                    ts     REAL NOT NULL
                )
                """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_ts ON cache(ts)")

    @staticmethod
    def create_unique_key(namespace: str, params: dict[str, Any]) -> str:
        """
        Create a deterministic cache key for the given namespace and parameters.

        Serializes the namespace and params (with sorted keys) to JSON and returns
        a SHA256 hex digest as the cache key.

        Args:
            namespace (str): Logical namespace for the cache entry (e.g. module name).
            params (dict[str, Any]): Parameters that uniquely identify the request.

        Returns:
            str: SHA256 hex digest representing the unique cache key.
        """
        raw = json.dumps({"ns": namespace, **params}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get_dataframe(
        self,
        namespace: str,
        params: dict[str, Any],
        ttl: int,
    ) -> pd.DataFrame | None:
        """
        Retrieve a cached DataFrame if present and not expired.

        Args:
            namespace (str): Logical namespace for the cache entry.
            params (dict[str, Any]): Parameters used to compute the cache key.
            ttl (int): Time-to-live in seconds. Entries older than this value are
                treated as missing and None is returned.

        Returns:
            pd.DataFrame | None: The cached DataFrame if found and fresh, otherwise None.
        """
        key = self.create_unique_key(namespace, params)
        with self._lock, sqlite3.connect(self._database_location) as conn:
            row = conn.execute(
                "SELECT value, ts FROM cache WHERE key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        value_json, ts = row
        if time.time() - ts > ttl:
            return None
        try:
            return pd.read_json(StringIO(value_json), dtype=False)
        except Exception:
            return None

    def store_dataframe(
        self, namespace: str, params: dict[str, Any], df: pd.DataFrame
    ) -> None:
        """
        Store a DataFrame in the cache under the computed key.

        If serialization of the DataFrame fails, the write is silently skipped
        so that a caching error never interrupts the calling code.

        Args:
            namespace (str): Logical namespace for the cache entry.
            params (dict[str, Any]): Parameters used to compute the cache key.
            df (pd.DataFrame): DataFrame to serialize and store.
        """
        key = self.create_unique_key(namespace, params)
        try:
            value_json = df.to_json()
        except Exception:
            return
        with self._lock, sqlite3.connect(self._database_location) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, value, ts) VALUES (?, ?, ?)",
                (key, value_json, time.time()),
            )

    def remove_expired_entries(self, ttl: int) -> int:
        """
        Evict cache entries older than the given TTL.

        Args:
            ttl (int): Time-to-live in seconds. Entries with a timestamp older
                than ``now - ttl`` are deleted from the database.

        Returns:
            int: Number of rows deleted.
        """
        cutoff = time.time() - ttl
        with self._lock, sqlite3.connect(self._database_location) as conn:
            cur = conn.execute("DELETE FROM cache WHERE ts < ?", (cutoff,))
            return cur.rowcount

    def clear_all(self) -> int:
        """
        Remove all entries from the cache regardless of age.

        Returns:
            int: Number of rows deleted.
        """
        with self._lock, sqlite3.connect(self._database_location) as conn:
            cur = conn.execute("DELETE FROM cache")
            return cur.rowcount
