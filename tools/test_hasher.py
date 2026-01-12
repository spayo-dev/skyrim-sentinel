"""
Tests for the Skyrim Sentinel hasher utility.
"""

import hashlib
import json
import tempfile
from pathlib import Path

import pytest

# Import the module under test
from hasher import hash_file, scan_directory, find_dll_files


class TestHashFile:
    """Tests for hash_file function."""
    
    def test_hash_known_content(self, tmp_path: Path):
        """Hash of known content should match expected value."""
        test_file = tmp_path / "test.bin"
        test_content = b"Hello, Skyrim Sentinel!"
        test_file.write_bytes(test_content)
        
        expected = hashlib.sha256(test_content).hexdigest()
        result = hash_file(test_file)
        
        assert result == expected
        assert len(result) == 64  # SHA-256 produces 64 hex chars
        
    def test_hash_empty_file(self, tmp_path: Path):
        """Empty file should produce valid hash."""
        test_file = tmp_path / "empty.bin"
        test_file.write_bytes(b"")
        
        expected = hashlib.sha256(b"").hexdigest()
        result = hash_file(test_file)
        
        assert result == expected
        
    def test_hash_large_file(self, tmp_path: Path):
        """Large file should be hashed correctly (tests chunking)."""
        test_file = tmp_path / "large.bin"
        # Create 1MB file
        large_content = b"x" * (1024 * 1024)
        test_file.write_bytes(large_content)
        
        expected = hashlib.sha256(large_content).hexdigest()
        result = hash_file(test_file)
        
        assert result == expected
        
    def test_hash_nonexistent_file(self, tmp_path: Path):
        """Nonexistent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            hash_file(tmp_path / "does_not_exist.dll")


class TestFindDllFiles:
    """Tests for find_dll_files function."""
    
    def test_finds_dll_files(self, tmp_path: Path):
        """Should find all .dll files recursively."""
        # Create test structure
        (tmp_path / "mod1").mkdir()
        (tmp_path / "mod1" / "plugin.dll").write_bytes(b"dll1")
        (tmp_path / "mod2").mkdir()
        (tmp_path / "mod2" / "other.dll").write_bytes(b"dll2")
        (tmp_path / "readme.txt").write_text("not a dll")
        
        results = list(find_dll_files(tmp_path))
        
        assert len(results) == 2
        filenames = {f.name for f in results}
        assert filenames == {"plugin.dll", "other.dll"}
        
    def test_empty_directory(self, tmp_path: Path):
        """Empty directory should return empty iterator."""
        results = list(find_dll_files(tmp_path))
        assert results == []


class TestScanDirectory:
    """Tests for scan_directory function."""
    
    def test_scan_returns_correct_structure(self, tmp_path: Path):
        """Scan should return list with correct keys."""
        (tmp_path / "test.dll").write_bytes(b"test content")
        
        results = scan_directory(tmp_path, verbose=False)
        
        assert len(results) == 1
        entry = results[0]
        assert "filename" in entry
        assert "path" in entry
        assert "sha256" in entry
        assert "size_bytes" in entry
        
    def test_scan_hash_accuracy(self, tmp_path: Path):
        """Scanned hash should match direct hash."""
        content = b"some dll content"
        (tmp_path / "verify.dll").write_bytes(content)
        
        results = scan_directory(tmp_path, verbose=False)
        
        expected = hashlib.sha256(content).hexdigest()
        assert results[0]["sha256"] == expected


class TestGoldenSetSchema:
    """Tests for golden_set.json structure."""
    
    def test_golden_set_valid_json(self):
        """golden_set.json should be valid JSON."""
        golden_set_path = Path(__file__).parent / "golden_set.json"
        
        with open(golden_set_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert "version" in data
        assert "plugins" in data
        assert isinstance(data["plugins"], list)
        
    def test_golden_set_has_required_fields(self):
        """Each plugin should have required fields."""
        golden_set_path = Path(__file__).parent / "golden_set.json"
        
        with open(golden_set_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for plugin in data["plugins"]:
            assert "name" in plugin, f"Plugin missing name: {plugin}"
            assert "nexusId" in plugin, f"Plugin missing nexusId: {plugin}"
            assert isinstance(plugin["nexusId"], int)
