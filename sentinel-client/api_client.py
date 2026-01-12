"""
Skyrim Sentinel - API Client Module

Communicates with the Sentinel verification API.
"""

from dataclasses import dataclass

import requests


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


@dataclass
class ScanResponse:
    """API scan response."""

    scanned: int
    verified: int
    unknown: int
    revoked: int
    results: list[ScanResult]


class SentinelAPIError(Exception):
    """Exception for API errors."""

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code


class SentinelClient:
    """
    Client for the Skyrim Sentinel verification API.
    """

    DEFAULT_URL = "http://localhost:8787"

    def __init__(self, base_url: str | None = None, timeout: int = 30):
        """
        Initialize the client.

        Args:
            base_url: API base URL (default: localhost for dev)
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
                )
            )

        return ScanResponse(
            scanned=data.get("scanned", 0),
            verified=data.get("verified", 0),
            unknown=data.get("unknown", 0),
            revoked=data.get("revoked", 0),
            results=results,
        )
