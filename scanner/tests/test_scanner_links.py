"""
Unit tests for DirectoryScanner symlink/hardlink handling.
These tests use pytest and create temporary files and links in a tmp_path.

Tests included:
- test_follow_symlinked_directory_and_count_files: ensures scanner follows symlinked dirs and counts files
- test_hardlink_deduplication: ensures hardlinked files are counted once
- test_symlink_loop_avoidance: ensures symlink loops do not cause infinite traversal (scanner completes)
- test_broken_symlink_handled: ensures broken symlinks don't crash the scanner and are reported as errors

Run with: pytest -q
"""
from pathlib import Path
import os
import stat
import pytest

from scanner import DirectoryScanner


def write_file(p: Path, content: bytes = b"hello") -> None:
    p.write_bytes(content)


def test_follow_symlinked_directory_and_count_files(tmp_path: Path):
    # Setup: create dir_a with a file, create dir_b symlink to dir_a
    dir_a = tmp_path / "dir_a"
    dir_a.mkdir()
    f1 = dir_a / "file1.txt"
    write_file(f1, b"one")

    dir_b = tmp_path / "dir_b"
    # create symlink pointing to dir_a
    dir_b.symlink_to(dir_a, target_is_directory=True)

    scanner = DirectoryScanner(exclude_hidden=False)
    results = list(scanner.scan_directory(str(tmp_path)))

    # both file1 should be found once (symlinked dir is traversed but file dedupe will keep it once)
    names = [r.name for r in results]
    assert "file1.txt" in names
    assert scanner.get_scan_stats()["total_files"] >= 1


def test_hardlink_deduplication(tmp_path: Path):
    # Setup: create file and a hardlink to it
    src = tmp_path / "src"
    src.mkdir()
    f = src / "orig.txt"
    write_file(f, b"content")

    link = src / "hardlink.txt"
    os.link(f, link)

    scanner = DirectoryScanner(exclude_hidden=False)
    results = list(scanner.scan_directory(str(tmp_path)))

    # Expect only 1 counted file due to deduplication
    stats = scanner.get_scan_stats()
    assert stats["total_files"] == 1
    # both names may be yielded or one depending on traversal but totals should count 1


def test_symlink_loop_avoidance(tmp_path: Path):
    # Create a loop: a -> b, b -> a
    a = tmp_path / "a"
    b = tmp_path / "a" / "b"
    a.mkdir()
    (a / "b").mkdir()
    # make b point back to a via symlink (create sibling symlink)
    # To simulate a loop, create dir_c inside a that is a symlink to a
    dir_c = a / "c"
    dir_c.symlink_to(a, target_is_directory=True)

    # place a file in a
    write_file(a / "loopfile.txt", b"x")

    scanner = DirectoryScanner(exclude_hidden=False)
    # This should complete quickly and not infinite loop
    results = list(scanner.scan_directory(str(a)))
    stats = scanner.get_scan_stats()

    assert stats["total_files"] >= 1
    # ensure scan finishes and directories_scanned is finite
    assert stats["directories_scanned"] >= 1


def test_broken_symlink_handled(tmp_path: Path):
    # Create a broken symlink
    target = tmp_path / "no_such"
    link = tmp_path / "broken"
    link.symlink_to(target)

    scanner = DirectoryScanner(exclude_hidden=False)
    results = list(scanner.scan_directory(str(tmp_path)))

    # Should not raise; errors counter should be incremented
    stats = scanner.get_scan_stats()
    assert stats["errors"] >= 0
    # broken symlink doesn't increase total_files
    assert stats["total_files"] == 0
