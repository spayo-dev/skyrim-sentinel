# Skyrim Sentinel Client

Desktop application for verifying SKSE plugin integrity.

## Quick Start

```bash
# Install dependencies
uv sync

# Run the app
uv run python main.py
```

## Building Standalone Executable

Create a standalone Windows `.exe` using Nuitka:

```bash
# Install build dependencies
uv sync --extra build

# Build the executable
uv run python build.py
```

The executable will be created at `dist/SkyrimSentinel.exe`.

### Optional: Add Custom Icon

Place an `icon.ico` file in the `assets/` folder before building.

## Features

- Folder picker for MO2/mods directory
- Fast SHA-256 hashing with progress tracking
- API verification against Golden Set database
- Modern dark-themed UI with color-coded results
- Click-to-copy hashes for easy sharing
- Export unknown hashes for community submission

## Contributing Hashes

Found unknown plugins? Help grow the database!

1. Click **Export Unknown** after scanning
2. Fill in `mod_name` and `nexus_id` in the exported JSON
3. Submit via GitHub issue or discussion
