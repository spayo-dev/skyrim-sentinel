"""
Skyrim Sentinel - Nuitka Build Script

Creates a standalone Windows executable using Nuitka.

Usage:
    uv run build.py

Output:
    dist/SkyrimSentinel.exe
"""

import subprocess
import sys
from pathlib import Path

from version import APP_NAME, __version__

# Build configuration
OUTPUT_DIR = Path("dist")
MAIN_SCRIPT = "main.py"
EXE_NAME = "SkyrimSentinel"

# Nuitka options
NUITKA_OPTIONS = [
    # Output settings
    f"--output-dir={OUTPUT_DIR}",
    f"--output-filename={EXE_NAME}.exe",
    # Standalone executable (includes Python runtime)
    "--standalone",
    "--onefile",
    # Windows-specific
    "--windows-console-mode=disable",  # No console window
    "--windows-icon-from-ico=assets/icon.ico" if Path("assets/icon.ico").exists() else "",
    # Include CustomTkinter assets
    "--include-package=customtkinter",
    "--include-data-dir=customtkinter=customtkinter",
    # Include our packages
    "--include-package=ui",
    # Include SQLite for local cache
    "--include-module=sqlite3",
    # Optimization
    "--assume-yes-for-downloads",  # Auto-download dependencies
    "--remove-output",  # Clean previous build
    # Metadata
    f"--product-name={APP_NAME}",
    f"--product-version={__version__}",
    f"--file-version={__version__}",
    "--company-name=Skyrim Sentinel",
    "--file-description=SKSE Plugin Integrity Checker",
    # Trade-off: faster build vs smaller size
    # Uncomment for smaller exe (slower build):
    # "--lto=yes",
]


def build():
    """Run Nuitka build."""
    print(f"Building {APP_NAME} v{__version__}...")
    print("=" * 50)

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Filter empty options
    options = [opt for opt in NUITKA_OPTIONS if opt]

    # Build command
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        *options,
        MAIN_SCRIPT,
    ]

    print(f"Running: {' '.join(cmd[:5])}...")
    print()

    try:
        subprocess.run(cmd, check=True)
        print()
        print("=" * 50)
        print("✅ Build successful!")
        print(f"   Output: {OUTPUT_DIR / EXE_NAME}.exe")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed with exit code {e.returncode}")
        return e.returncode
    except FileNotFoundError:
        print("❌ Nuitka not found. Install with:")
        print("   uv add nuitka")
        return 1


if __name__ == "__main__":
    sys.exit(build())
