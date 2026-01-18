"""
Skyrim Sentinel - DLL Hasher Utility

Generates SHA-256 hashes for DLL files in a memory-efficient manner.
Used to build and update the Golden Set database.
"""

import hashlib
import json
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

# 64KB chunks for memory-efficient hashing
CHUNK_SIZE = 65536


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


def find_dll_files(directory: Path) -> Iterator[Path]:
    """
    Recursively find all .dll files in a directory.

    Args:
        directory: Root directory to search

    Yields:
        Path objects for each .dll file found
    """
    yield from directory.rglob("*.dll")


def scan_directory(directory: Path, verbose: bool = True) -> list[dict]:
    """
    Scan a directory for DLL files and generate hashes.

    Args:
        directory: Directory to scan
        verbose: Print progress to stderr

    Returns:
        List of dicts with filename, path, and sha256 keys
    """
    results = []
    dll_files = list(find_dll_files(directory))
    total = len(dll_files)

    for i, dll_path in enumerate(dll_files, 1):
        if verbose:
            print(f"[{i}/{total}] Hashing: {dll_path.name}", file=sys.stderr)

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
            print(f"  [ERROR] {e}", file=sys.stderr)

    return results


def update_golden_set(
    hashes: list[dict],
    manifest_path: Path,
    plugin_name: str | None = None,
) -> None:
    """
    Update golden_set.json with new hash entries.

    Args:
        hashes: List of hash results from scan_directory
        manifest_path: Path to golden_set.json
        plugin_name: If specified, add hashes only to this plugin
    """
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    manifest["generated"] = datetime.now(UTC).isoformat()

    if plugin_name:
        # Add to specific plugin
        for plugin in manifest["plugins"]:
            if plugin["name"] == plugin_name:
                for h in hashes:
                    plugin["files"].append(
                        {
                            "filename": h["filename"],
                            "sha256": h["sha256"],
                            "size_bytes": h["size_bytes"],
                            "status": "pending",
                            "added": datetime.now(UTC).isoformat(),
                        }
                    )
                break

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def export_for_kv(manifest_path: Path, output_path: Path) -> None:
    """
    Export golden_set.json to Cloudflare KV bulk upload format.

    Creates a JSON array of {key, value} objects for wrangler kv:bulk put.

    Args:
        manifest_path: Path to golden_set.json
        output_path: Path to write KV bulk upload file
    """
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    kv_entries = []

    for plugin in manifest["plugins"]:
        for file_entry in plugin.get("files", []):
            if file_entry.get("sha256"):
                kv_entries.append(
                    {
                        "key": f"sha256:{file_entry['sha256']}",
                        "value": json.dumps(
                            {
                                "name": plugin["name"],
                                "nexusId": plugin["nexusId"],
                                "filename": file_entry["filename"],
                                "status": file_entry.get("status", "verified"),
                            }
                        ),
                    }
                )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(kv_entries, f, indent=2)

    print(f"Exported {len(kv_entries)} entries to {output_path}", file=sys.stderr)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Skyrim Sentinel - DLL Hash Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # scan command
    scan_parser = subparsers.add_parser("scan", help="Scan directory for DLLs")
    scan_parser.add_argument("directory", type=Path, help="Directory to scan")
    scan_parser.add_argument("--output", "-o", type=Path, help="Output JSON file (default: stdout)")

    # hash command
    hash_parser = subparsers.add_parser("hash", help="Hash a single file")
    hash_parser.add_argument("file", type=Path, help="File to hash")

    # export command
    export_parser = subparsers.add_parser("export", help="Export to KV format")
    export_parser.add_argument(
        "--manifest",
        "-m",
        type=Path,
        default=Path(__file__).parent / "golden_set.json",
        help="Path to golden_set.json",
    )
    export_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path(__file__).parent / "kv_bulk.json",
        help="Output path for KV bulk file",
    )

    args = parser.parse_args()

    if args.command == "scan":
        results = scan_directory(args.directory)
        output = json.dumps(results, indent=2)

        if args.output:
            args.output.write_text(output)
            print(f"Wrote {len(results)} entries to {args.output}", file=sys.stderr)
        else:
            print(output)

    elif args.command == "hash":
        if not args.file.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        print(hash_file(args.file))

    elif args.command == "export":
        export_for_kv(args.manifest, args.output)


if __name__ == "__main__":
    main()
