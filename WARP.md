# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

Comic File Organizer is a Python tool for managing comic book files. The project's goal is to scan, rename, and import comic files: convert CBR→CBZ, rename per Mylar rules, move to filestore, and update Mylar3 database.

The project includes:
- An embedded DFA (Disk-Folder-File Analyzer) utility in `comic_file_organizer/dfa/` that provides comprehensive directory scanning and file analysis capabilities
- Mylar3 integration modules for analyzing comic collections based on Mylar3's config.ini and file structure conventions

## Common Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
. .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Run the CLI stub (main application still in development)
python3 -m comic_file_organizer.cli

# Run the embedded DFA scanner
python3 comic_file_organizer/dfa/main.py /path/to/directory
python3 comic_file_organizer/dfa/main.py -s count -m 20 -o results.txt

# Run Mylar3 statistics analyzer
python3 -m comic_file_organizer.mylar3_cli /path/to/mylar3/config.ini
```

### Testing
```bash
# Run all tests
python3 -m pytest

# Run specific test file
python3 -m pytest tests/test_comicvine_cache.py
python3 -m pytest comic_file_organizer/tests/test_scanner_links.py

# Run tests with verbose output
python3 -m pytest -v

# Run tests quietly
python3 -m pytest -q
```

### Makefile Targets
```bash
# Create virtual environment and install dependencies
make venv

# Run tests (currently a stub)
make test

# Clean up generated files
make clean
```

### Module Testing
```bash
# Test individual modules standalone
python3 comic_file_organizer/dfa/config.py
python3 comic_file_organizer/dfa/scanner.py /path/to/test
python3 comic_file_organizer/dfa/stats.py /path/to/test
python3 comic_file_organizer/dfa/output.py

# Test ComicVine cache module
python3 comicvine_cache.py
```

## Architecture Overview

### Project Structure

```
comic-file-organizer/
├── comic_file_organizer/          # Main package
│   ├── __init__.py               # Version info
│   ├── cli.py                    # Main CLI entry point (stub)
│   ├── dfa/                      # Embedded DFA scanner utility
│   │   ├── main.py              # DFA CLI interface
│   │   ├── config.py            # Configuration management
│   │   ├── scanner.py           # Directory scanning engine
│   │   ├── stats.py             # Statistics calculation
│   │   ├── output.py            # Output formatting
│   │   └── config.json          # DFA configuration
│   └── tests/                    # DFA-specific tests
│       └── test_scanner_links.py
├── comicvine_cache.py            # SQLite-backed ComicVine API cache
├── tests/                        # Top-level tests
│   └── test_comicvine_cache.py
├── requirements.txt              # rarfile>=4.2
└── Makefile                      # Build automation
```

### ComicVine Cache (`comicvine_cache.py`)

**Purpose**: SQLite-backed cache for ComicVine API metadata to minimize API calls and improve performance.

**Key Features**:
- TTL-based expiration (default 86400 seconds / 24 hours)
- Thread-safe SQLite operations with `check_same_thread=False`
- Graceful handling of stale data and failed fetches
- `fetch_or_get()` pattern: check cache → if stale/missing, fetch → store → return

**Usage Pattern**:
```python
cache = ComicVineCache(db_path="./comicvine_cache.db", ttl_seconds=86400)
data = cache.fetch_or_get(issue_id, fetcher_callable)
cache.close()
```

The `fetcher_callable` should accept an `issue_id` string and return a dict of metadata.

### DFA Scanner Architecture

The DFA (Disk-Folder-File Analyzer) is a fully-featured file system analysis tool integrated into this project. See `comic_file_organizer/dfa/WARP.md` for detailed documentation.

**Core Components**:
- **`scanner.py`**: Generator-based directory traversal with symlink following, hardlink deduplication, and loop prevention
- **`stats.py`**: Streaming statistics calculation using `FileInfo` → `ExtensionStats` → `ScanStatistics` data flow
- **`output.py`**: Professional table formatting with human-readable sizes
- **`config.py`**: JSON configuration with CLI override support
- **`main.py`**: Signal handling, argument parsing, orchestration

**Key Architectural Patterns**:
- **Generator-based processing**: Memory-efficient handling of large directories (tested with 59K+ files)
- **Inode tracking**: Deduplicates hardlinks and detects symlink loops using (device, inode) tuples
- **Streaming statistics**: Processes files one-by-one without loading all data into memory
- **Graceful error handling**: Continues on permission errors, logs issues, supports Ctrl+C interruption

**Symlink and Hardlink Behavior**:
- Follows symlinked directories (`os.walk(followlinks=True)`)
- Tracks directory inodes to prevent infinite loops from circular symlinks
- Tracks file inodes to deduplicate hardlinks (only counts first occurrence)
- Uses `os.stat()` (not `lstat()`) to get target file sizes for symlinked files

## Development Guidelines

### Testing Strategy

When adding new features, write tests following the existing patterns:
- Use pytest for test framework
- Use `:memory:` SQLite databases for cache tests to avoid filesystem dependencies
- Use `tempfile.TemporaryDirectory()` for scanner tests that need real filesystem operations
- Test edge cases: broken symlinks, permission errors, TTL expiration, hardlinks, symlink loops

### Code Style

- Follow existing patterns: dataclasses for structured data, type hints where helpful
- Use logging (not print) for debug information in library code
- Maintain modular separation: each module should have a single clear responsibility
- Include docstrings with type information for public APIs
- Each module should be runnable standalone with `if __name__ == "__main__":` test code

### Error Handling

- Validate and sanitize all user input paths
- Use try/except with logging for operations that may fail (file access, network calls)
- Provide graceful degradation: continue processing when individual operations fail
- Use appropriate log levels: DEBUG (detailed), INFO (progress), WARNING (issues), ERROR (failures)

### Adding Features

**To extend ComicVine cache**:
1. Add methods to `ComicVineCache` class
2. Write corresponding tests in `tests/test_comicvine_cache.py`
3. Update docstring if changing the API contract

**To extend DFA scanner**:
1. See detailed guidelines in `comic_file_organizer/dfa/WARP.md`
2. Maintain generator pattern for memory efficiency
3. Add corresponding tests in `comic_file_organizer/tests/test_scanner_links.py`

**To extend main CLI**:
1. Update `comic_file_organizer/cli.py` (currently a stub)
2. Consider using `argparse` for argument parsing
3. Follow the DFA pattern: configuration → processing → output

## Integration Notes

### DFA Integration

The DFA code was integrated via vendor-copy (not git subtree) from a separate project. Full integration history is preserved in `CONVERSATION.md`. The DFA maintains its own documentation at `comic_file_organizer/dfa/WARP.md` and `comic_file_organizer/dfa/README.md`.

### External Documentation

- Central docs index: `../docs/DOCUMENTATION_INDEX.md`
- Project conversation history: `CONVERSATION.md`
- DFA-specific conversation log: `comic_file_organizer/dfa/CONVERSATION.md` (if it exists)

## Mylar3 Integration

### Overview

The Mylar3 statistics module analyzes comic collections organized according to Mylar3 conventions. It reads the Mylar3 `config.ini` file to understand the collection structure and calculates comprehensive statistics about publishers, series, and issues.

### Mylar3 File Structure

**Hierarchy**: `destination_dir` → Publishers → Series → Issues

```
comicbooks/                           # destination_dir from config.ini
├── .zzz_check                        # Zero-length marker file
├── Marvel/                           # Publisher directory
│   ├── The Amazing Spider-Man (1963)/   # Series directory
│   │   ├── series.json              # Series metadata (required)
│   │   ├── cvinfo                   # ComicVine API URL (optional)
│   │   └── [no issue files]         # Series followed but no issues owned
│   └── The Amazing Spider-Man (2025)/
│       ├── series.json
│       ├── cvinfo
│       ├── The Amazing Spider-Man #001 (June 2025).cbz
│       ├── The Amazing Spider-Man #002 (June 2025).cbz
│       └── The Amazing Spider-Man #003 (July 2025).cbz
└── DC Comics/
    └── ...
```

**Validation Rules**:
- Publisher directories (level 1): Only `.zzz_check` file allowed at root, must be zero-length
- Publisher directories with no series subdirectories are ignored
- Series directories (level 2): Should contain no files except `series.json`, `cvinfo`, and comic files (`.cbr`, `.cbz`)
- Series directory must contain `series.json` to be valid

### config.ini Structure

**Key Configuration Values** (under `[General]`):

```ini
[General]
destination_dir = /path/to/comicbooks     # Root of comic collection
folder_format = $Publisher/$Series $Type ($Year)   # Directory naming convention
file_format = $Series $VolumeN $Annual #$Issue ($monthname $Year)  # File naming convention
```

**Naming Convention Variables**: See [Mylar3 documentation](https://github.com/mylar3/mylar3/wiki) for complete list of variables used in `folder_format` and `file_format`.

### series.json Structure

**Key Fields**:
```json
{
    "version": "1.0.2",
    "metadata": {
        "publisher": "Marvel",
        "name": "The Amazing Spider-Man",
        "comicid": 163325,
        "year": 2025,
        "total_issues": 14,           # Total expected issues
        "publication_run": "June 2025 - Present",
        "status": "Continuing"         # or "Ended"
    }
}
```

### Statistics Definitions

**Publisher Level**:
- **Total Publishers**: Count of directories under `destination_dir` (excluding `.zzz_check`)
- **Publishers with Series**: Publishers that have at least one series subdirectory

**Series Level**:
- **Series Followed**: Series with zero CBR/CBZ files (tracking only)
- **Series with Issues**: Series with at least one CBR/CBZ file
- **Complete Series**: Series where `issues_owned == total_issues` from `series.json`
- **Series per Publisher**: Breakdown of series count by publisher

**Issue Level**:
- **Issues Owned**: Count of distinct CBR/CBZ files matching `file_format` pattern in each series directory
- **Missing Issues**: `total_issues - issues_owned` for each series
- **Total Issues Owned**: Sum across all series
- **Total Missing Issues**: Sum across all series

**Additional Statistics**:
- Average completion percentage per series
- Average issues per series
- Largest collections by publisher
- Series closest to completion
- Most incomplete series

### Usage Pattern

```python
from comic_file_organizer.mylar3_config import Mylar3Config
from comic_file_organizer.mylar3_scanner import Mylar3Scanner
from comic_file_organizer.mylar3_stats import calculate_statistics

# Load Mylar3 configuration
config = Mylar3Config("/path/to/mylar3/config.ini")

# Scan the collection
scanner = Mylar3Scanner(config.destination_dir)
results = scanner.scan()

# Calculate statistics
stats = calculate_statistics(results)
print(stats.summary())
```

## Dependencies

- **rarfile>=4.2**: Required for CBR (RAR comic archive) handling
- **pytest**: Development dependency for running tests (not in requirements.txt)

No other external dependencies currently. The project uses standard library modules for most functionality.
