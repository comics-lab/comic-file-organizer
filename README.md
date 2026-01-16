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

## Action Log
- 2025-10-19 — Initialized repository skeleton (MIT, Python 3 only).

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
