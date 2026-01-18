"""
Skyrim Sentinel - API Client Module

Communicates with the Sentinel verification API.
Supports hybrid mode: remote-first with local cache fallback.
"""

from dataclasses import dataclass
from typing import Literal

import requests

from local_cache import LocalCache, init_cache_from_golden_set


@dataclass
class PluginInfo:
    """Plugin metadata from verification."""

    name: str
    nexus_id: int
    filename: str | None = None
    author: str | None = None


@dataclass
class ScanResult:
    """Individual hash verification result."""

    hash: str
    status: str  # "verified", "unknown", "revoked"
    plugin: PluginInfo | None = None
    source: Literal["remote", "cached"] = "remote"


@dataclass
class ScanResponse:
    """API scan response."""

    scanned: int
    verified: int
    unknown: int
    revoked: int
    results: list[ScanResult]
    source: Literal["remote", "cached", "mixed"] = "remote"


class SentinelAPIError(Exception):
    """Exception for API errors."""

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code


class SentinelClient:
    """
    Client for the Skyrim Sentinel verification API.
    """

    # Production Cloudflare Worker URL
    DEFAULT_URL = "https://sentinel-worker.seanpayomo-work.workers.dev"

    def __init__(self, base_url: str | None = None, timeout: int = 30):
        """
        Initialize the client.

        Args:
            base_url: API base URL (default: production worker)
            timeout: Request timeout in seconds
        """
        self.base_url = (base_url or self.DEFAULT_URL).rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": "SkyrimSentinel/1.0",
            }
        )

    def health_check(self) -> bool:
        """
        Check if the API is available.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=self.timeout,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def scan(self, hashes: list[str]) -> ScanResponse:
        """
        Submit hashes for verification.

        Args:
            hashes: List of SHA-256 hash strings

        Returns:
            ScanResponse with verification results

        Raises:
            SentinelAPIError: On API errors
            requests.RequestException: On network errors
        """
        if not hashes:
            raise ValueError("Hashes list cannot be empty")

        response = self.session.post(
            f"{self.base_url}/api/v1/scan",
            json={"hashes": hashes},
            timeout=self.timeout,
        )

        data = response.json()

        if response.status_code != 200:
            raise SentinelAPIError(
                data.get("error", "Unknown error"),
                data.get("code"),
            )

        # Parse results
        results = []
        for item in data.get("results", []):
            plugin = None
            if item.get("plugin"):
                plugin = PluginInfo(
                    name=item["plugin"]["name"],
                    nexus_id=item["plugin"]["nexusId"],
                    filename=item["plugin"].get("filename"),
                    author=item["plugin"].get("author"),
                )

            results.append(
                ScanResult(
                    hash=item["hash"],
                    status=item["status"],
                    plugin=plugin,
                    source="remote",
                )
            )

        return ScanResponse(
            scanned=data.get("scanned", 0),
            verified=data.get("verified", 0),
            unknown=data.get("unknown", 0),
            revoked=data.get("revoked", 0),
            results=results,
            source="remote",
        )


class HybridVerifier:
    """
    Hybrid verifier with remote-first, local-fallback strategy.

    Tries the Cloudflare Worker first for up-to-date security data.
    Falls back to local cache for offline use or network issues.
    """

    def __init__(
        self,
        remote_timeout: int = 5,
        base_url: str | None = None,
        cache: LocalCache | None = None,
    ):
        """
        Initialize the hybrid verifier.

        Args:
            remote_timeout: Timeout for remote API calls (default: 5s)
            base_url: Override remote API URL
            cache: Optional pre-initialized LocalCache
        """
        self.client = SentinelClient(base_url=base_url, timeout=remote_timeout)
        self.cache = cache or init_cache_from_golden_set()
        self._last_source: Literal["remote", "cached"] = "cached"

    @property
    def last_source(self) -> Literal["remote", "cached"]:
        """Source used for the last verification."""
        return self._last_source

    def verify(self, hashes: list[str]) -> ScanResponse:
        """
        Verify hashes using remote-first, local-fallback strategy.

        Args:
            hashes: List of SHA-256 hashes to verify

        Returns:
            ScanResponse with results (includes source field)
        """
        if not hashes:
            raise ValueError("Hashes list cannot be empty")

        # Try remote first
        try:
            response = self.client.scan(hashes)
            self._last_source = "remote"
            return response
        except (requests.RequestException, SentinelAPIError) as e:
            # Log but don't fail - fall back to cache
            print(f"[HybridVerifier] Remote failed ({e}), using local cache")

        # Fallback to local cache
        self._last_source = "cached"
        return self._verify_from_cache(hashes)

    def _verify_from_cache(self, hashes: list[str]) -> ScanResponse:
        """Verify hashes using local cache."""
        cache_results = self.cache.get_batch(hashes)

        results = []
        verified = 0
        unknown = 0
        revoked = 0

        for hash_str, cached in cache_results.items():
            if cached is None:
                unknown += 1
                results.append(
                    ScanResult(
                        hash=hash_str,
                        status="unknown",
                        plugin=None,
                        source="cached",
                    )
                )
            elif cached.status == "revoked":
                revoked += 1
                results.append(
                    ScanResult(
                        hash=hash_str,
                        status="revoked",
                        plugin=PluginInfo(
                            name=cached.name,
                            nexus_id=cached.nexus_id,
                            filename=cached.filename,
                        ),
                        source="cached",
                    )
                )
            else:
                verified += 1
                results.append(
                    ScanResult(
                        hash=hash_str,
                        status="verified",
                        plugin=PluginInfo(
                            name=cached.name,
                            nexus_id=cached.nexus_id,
                            filename=cached.filename,
                        ),
                        source="cached",
                    )
                )

        return ScanResponse(
            scanned=len(hashes),
            verified=verified,
            unknown=unknown,
            revoked=revoked,
            results=results,
            source="cached",
        )

    def is_online(self) -> bool:
        """Check if remote API is available."""
        return self.client.health_check()

    def sync_cache(self) -> int:
        """
        Sync local cache from golden_set.json.

        Returns:
            Number of entries synced
        """
        return self.cache.load_from_golden_set()
