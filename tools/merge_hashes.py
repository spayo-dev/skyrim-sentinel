"""
Skyrim Sentinel - Hash Merge Utility

Merges new_hashes.json into golden_set.json, creating plugin entries as needed.
"""

import json
from datetime import UTC, datetime
from pathlib import Path


def merge_hashes() -> None:
    """Merge newly scanned hashes from new_hashes.json into golden_set.json."""
    golden_path = Path("tools/golden_set.json")
    new_hashes_path = Path("tools/new_hashes.json")

    with open(golden_path, encoding="utf-8") as f:
        golden = json.load(f)

    with open(new_hashes_path, encoding="utf-8") as f:
        new_hashes = json.load(f)

    plugins_map = {p["name"]: p for p in golden["plugins"]}

    for entry in new_hashes:
        path_parts = entry["path"].split("\\")
        if len(path_parts) < 2:
            print(f"Skipping invalid path: {entry['path']}")
            continue

        plugin_name = path_parts[0]

        if plugin_name not in plugins_map:
            # Create new plugin entry
            new_plugin = {
                "name": plugin_name,
                "nexusId": 0,  # Placeholder
                "files": [],
            }
            golden["plugins"].append(new_plugin)
            plugins_map[plugin_name] = new_plugin

        plugin = plugins_map[plugin_name]

        # Check if file exists
        if any(f["filename"] == entry["filename"] for f in plugin["files"]):
            continue

        plugin["files"].append(
            {
                "filename": entry["filename"],
                "sha256": entry["sha256"],
                "size_bytes": entry["size_bytes"],
                "status": "verified",  # Assuming local scan is trusted
                "added": datetime.now(UTC).isoformat(),
            }
        )
        print(f"Added {entry['filename']} to {plugin_name}")

    golden["version"] = datetime.now(UTC).strftime("%Y.%m.%d")

    with open(golden_path, "w", encoding="utf-8") as f:
        json.dump(golden, f, indent=2)

    print("Merge complete.")


if __name__ == "__main__":
    merge_hashes()
