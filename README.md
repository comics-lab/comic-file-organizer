# comic-file-organizer

## Agent and Logs

- Agent profile: `AGENTS.md`
- Logs (local-only): `CONVERSATION.md`, `BOOKMARKS.md`, `Action-Log.md` (when present)


Scan/rename/import: convert CBR→CBZ, rename per Mylar rules, move to filestore, update Mylar3.

## Documentation

- Central docs index: `../docs/DOCUMENTATION_INDEX.md`
- Conversation snapshot (docs): `../docs/conversations/comic-file-organizer.md`
- Canonical conversation transcript: `CONVERSATION.md`

## Quickstart
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Mylar3 Collection Scanner

The scanner analyzes Mylar3 comic collections and provides detailed statistics.

### Usage

**Summary Report (default):**
```bash
python3 -m comic_file_organizer.mylar3_cli /path/to/mylar3/config.ini
```

This generates a summary report showing:
- Total publishers, series, and issues
- Publisher breakdown
- Series details
- Most incomplete/complete series

**Publisher Detail Report:**
```bash
python3 -m comic_file_organizer.mylar3_cli /path/to/mylar3/config.ini --publisher Marvel
```

This generates a detailed report for a specific publisher showing:
- Series count
- File types (CBR, CBZ, etc.) per series with counts and sizes
- Totals per series and per publisher

The `--publisher` parameter is case-insensitive, so `--publisher marvel`, `--publisher MARVEL`, or `--publisher Marvel` all work.

### Features

- **File Type Tracking**: Tracks CBR, CBZ, and other comic file types separately
- **Size Analysis**: Reports disk space usage per file type and per series
- **Case-Insensitive Publisher Matching**: Find publishers regardless of case
- **Human-Readable Sizes**: File sizes displayed in B, KB, MB, GB format

## Action Log
- 2025-10-19 — Initialized repository skeleton (MIT, Python 3 only).
- 2025-01-XX — Enhanced scanner with file type tracking and detailed publisher reports.

## Appendix: Directory Structure — comic-file-organizer

<!-- BEGIN DIR TREE -->
```
comic-file-organizer
├── comic_file_organizer
│   ├── __init__.py
│   └── cli.py
├── LICENSE
├── Makefile
├── README.md
└── requirements.txt
```
<!-- END DIR TREE -->
