"""
Skyrim Sentinel - PyInstaller Build Script

Creates a standalone Windows executable using PyInstaller.

Usage:
    uv sync --extra build
    uv run python build.py

Output:
    dist/SkyrimSentinel.exe
"""

import shutil
import subprocess
import sys
from pathlib import Path

from version import APP_NAME, __version__

# Build configuration
OUTPUT_DIR = Path("dist")
MAIN_SCRIPT = "main.py"
EXE_NAME = "SkyrimSentinel"


def get_customtkinter_path() -> Path | None:
    """Find the customtkinter package installation path."""
    try:
        import customtkinter

        return Path(customtkinter.__file__).parent
    except ImportError:
        return None


def build():
    """Run PyInstaller build."""
    print(f"Building {APP_NAME} v{__version__}...")
    print("=" * 50)

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Find customtkinter for data inclusion
    ctk_path = get_customtkinter_path()
    if not ctk_path:
        print("❌ customtkinter not found. Run 'uv sync' first.")
        return 1

    # Check for icon
    icon_path = Path("assets/icon.ico")

    # PyInstaller command
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--windowed",
        "--clean",
        f"--name={EXE_NAME}",
        f"--distpath={OUTPUT_DIR}",
        # Include customtkinter data files (themes, etc.)
        f"--add-data={ctk_path};customtkinter",
        # Hidden imports that PyInstaller might miss
        "--hidden-import=PIL._tkinter_finder",
        MAIN_SCRIPT,
    ]

    # Add icon if exists
    if icon_path.exists():
        cmd.insert(-1, f"--icon={icon_path}")

    print("Running: PyInstaller...")
    print()

    try:
        subprocess.run(cmd, check=True)
        print()
        print("=" * 50)
        print("✅ Build successful!")
        print(f"   Output: {OUTPUT_DIR / EXE_NAME}.exe")

        # Clean up build artifacts
        build_dir = Path("build")
        spec_file = Path(f"{EXE_NAME}.spec")
        if build_dir.exists():
            print("   Cleaning build artifacts...")
            shutil.rmtree(build_dir)
        if spec_file.exists():
            spec_file.unlink()

        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed with exit code {e.returncode}")
        return e.returncode
    except FileNotFoundError:
        print("❌ PyInstaller not found. Install with:")
        print("   uv sync --extra build")
        return 1


if __name__ == "__main__":
    sys.exit(build())
