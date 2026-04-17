# Duplicate File Detector

Scans a directory tree for duplicate files using MD5 hashing. Groups by file size first (fast), then hashes only the candidates — efficient even on large drives.

## Features

- Size-first grouping avoids hashing unique files
- Configurable minimum file size filter
- Skips common junk dirs (`.git`, `node_modules`, `__pycache__`, `venv`)
- Prints ranked report by wasted space
- Optional JSON output for scripting

## Usage

```bash
# Scan current directory
python3 duplicate_detector.py

# Scan a specific path
python3 duplicate_detector.py /path/to/scan

# Set minimum file size (bytes) and exclude dirs
python3 duplicate_detector.py ~/Downloads --min-size 10240 --exclude .git build dist

# Save full JSON report
python3 duplicate_detector.py ~/Documents --output report.json
```

## Output

```
=== DUPLICATE FILE DETECTION REPORT ===

SCAN STATISTICS:
  Total Files Scanned: 12,483
  Wasted Space: 2.3 GB

TOP DUPLICATE GROUPS:
  Group #1: 4 copies — Wasted: 843.2 MB
    photo_backup_2023.zip
    photo_backup_2023 (copy).zip
    ...
```
