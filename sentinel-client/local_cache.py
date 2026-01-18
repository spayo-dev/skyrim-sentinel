"""
Skyrim Sentinel - Local Cache Module

SQLite-based local cache for offline verification.
Loaded from golden_set.json for fallback when remote API unavailable.
"""

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CachedPlugin:
    """Cached plugin info from local database."""

    name: str
    nexus_id: int
    filename: str | None = None
    status: str = "verified"


class LocalCache:
    """
    SQLite-based local cache for hash verification.

    Provides offline verification capability when the remote
    Cloudflare Worker is unavailable.
    """

    # Default paths
    DEFAULT_CACHE_PATH = Path(__file__).parent / "cache" / "sentinel.db"
    DEFAULT_GOLDEN_SET = Path(__file__).parent.parent / "tools" / "golden_set.json"

    def __init__(self, db_path: Path | None = None):
        """
        Initialize the local cache.

        Args:
            db_path: Path to SQLite database (default: cache/sentinel.db)
        """
        self.db_path = db_path or self.DEFAULT_CACHE_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hashes (
                    sha256 TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    nexus_id INTEGER NOT NULL,
                    filename TEXT,
                    status TEXT DEFAULT 'verified',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON hashes(status)
            """)
            conn.commit()

    def get(self, sha256: str) -> CachedPlugin | None:
        """
        Look up a hash in the local cache.

        Args:
            sha256: SHA-256 hash string (lowercase)

        Returns:
            CachedPlugin if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT name, nexus_id, filename, status FROM hashes WHERE sha256 = ?",
                (sha256.lower(),),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return CachedPlugin(
                name=row["name"],
                nexus_id=row["nexus_id"],
                filename=row["filename"],
                status=row["status"],
            )

    def get_batch(self, hashes: list[str]) -> dict[str, CachedPlugin | None]:
        """
        Look up multiple hashes in batches.

        Args:
            hashes: List of SHA-256 hashes

        Returns:
            Dict mapping hash -> CachedPlugin (or None if not found)
        """
        results = {}
        normalized = [h.lower() for h in hashes]

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            # SQLite has a limit on parameters, process in chunks
            chunk_size = 500
            for i in range(0, len(normalized), chunk_size):
                chunk = normalized[i : i + chunk_size]
                placeholders = ",".join("?" * len(chunk))
                cursor = conn.execute(
                    f"SELECT sha256, name, nexus_id, filename, status FROM hashes WHERE sha256 IN ({placeholders})",
                    chunk,
                )
                for row in cursor:
                    results[row["sha256"]] = CachedPlugin(
                        name=row["name"],
                        nexus_id=row["nexus_id"],
                        filename=row["filename"],
                        status=row["status"],
                    )

        # Fill in None for hashes not found
        for h in normalized:
            if h not in results:
                results[h] = None

        return results

    def load_from_golden_set(self, golden_set_path: Path | None = None) -> int:
        """
        Load cache from golden_set.json file.

        Args:
            golden_set_path: Path to golden_set.json

        Returns:
            Number of entries loaded
        """
        path = golden_set_path or self.DEFAULT_GOLDEN_SET

        if not path.exists():
            raise FileNotFoundError(f"Golden set not found: {path}")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        with sqlite3.connect(self.db_path) as conn:
            for plugin in data.get("plugins", []):
                for file_entry in plugin.get("files", []):
                    sha256 = file_entry.get("sha256")
                    if sha256:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO hashes
                            (sha256, name, nexus_id, filename, status)
                            VALUES (?, ?, ?, ?, ?)
                        """,
                            (
                                sha256.lower(),
                                plugin["name"],
                                plugin["nexusId"],
                                file_entry.get("filename"),
                                file_entry.get("status", "verified"),
                            ),
                        )
                        count += 1
            conn.commit()

        return count

    def count(self) -> int:
        """Return number of entries in cache."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM hashes")
            return cursor.fetchone()[0]

    def clear(self) -> None:
        """Clear all entries from cache."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM hashes")
            conn.commit()


def init_cache_from_golden_set() -> LocalCache:
    """
    Initialize cache and load from golden_set.json.

    Returns:
        Initialized LocalCache instance
    """
    cache = LocalCache()
    if cache.count() == 0:
        try:
            count = cache.load_from_golden_set()
            print(f"[LocalCache] Loaded {count} entries from golden_set.json")
        except FileNotFoundError:
            print("[LocalCache] Warning: golden_set.json not found, cache empty")
    return cache
