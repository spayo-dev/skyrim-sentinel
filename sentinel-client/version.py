"""
Skyrim Sentinel - Version Information

Uses Semantic Versioning (SemVer): MAJOR.MINOR.PATCH
- MAJOR: Breaking changes
- MINOR: New features (backwards compatible)
- PATCH: Bug fixes (backwards compatible)

Pre-release: 0.x.x indicates beta/development phase
"""

__version__ = "0.1.0"
__version_info__ = tuple(int(x) for x in __version__.split("."))

# Build metadata
APP_NAME = "Skyrim Sentinel"
APP_AUTHOR = "Skyrim Sentinel Team"
APP_DESCRIPTION = "SKSE Plugin Integrity Checker"
