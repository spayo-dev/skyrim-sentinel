"""
Skyrim Sentinel - DLL Scanner Module

Discovers and hashes DLL files in mod directories.
"""

import hashlib
from pathlib import Path
from typing import Callable, Iterator

# 64KB chunks for memory-efficient hashing
CHUNK_SIZE = 65536


def find_dlls(directory: Path) -> Iterator[Path]:
    """
    Recursively find all .dll files in a directory.

    Args:
        directory: Root directory to search

    Yields:
        Path objects for each .dll file found
    """
    yield from directory.rglob("*.dll")


def hash_file(file_path: Path) -> str:
    """
    Generate SHA-256 hash of a file using chunked reading.

    Args:
        file_path: Path to the file to hash

    Returns:
        Lowercase hex string of the SHA-256 hash

    Raises:
        FileNotFoundError: If the file doesn't exist
        PermissionError: If the file can't be read
    """
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            sha256.update(chunk)

    return sha256.hexdigest()


def scan_directory(
    directory: Path,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> list[dict]:
    """
    Scan a directory for DLL files and generate hashes.

    Args:
        directory: Directory to scan
        progress_callback: Optional callback(current, total, filename)

    Returns:
        List of dicts with filename, path, and sha256 keys
    """
    results = []
    dll_files = list(find_dlls(directory))
    total = len(dll_files)

    for i, dll_path in enumerate(dll_files, 1):
        if progress_callback:
            progress_callback(i, total, dll_path.name)

        try:
            file_hash = hash_file(dll_path)
            results.append(
                {
                    "filename": dll_path.name,
                    "path": str(dll_path.relative_to(directory)),
                    "sha256": file_hash,
                    "size_bytes": dll_path.stat().st_size,
                }
            )
        except (PermissionError, OSError) as e:
            results.append(
                {
                    "filename": dll_path.name,
                    "path": str(dll_path.relative_to(directory)),
                    "sha256": None,
                    "error": str(e),
                }
            )

    return results
