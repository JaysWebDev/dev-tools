# Cache Cleanup 🧹

Clears Python bytecode, pip/npm caches, snap browser caches, fontconfig, mesa shader cache, and user trash. Machine-aware — uses `$HOME`, not hardcoded paths. Supports `--dry-run`. Safe to run anytime or schedule via cron.

Part of [dev-tools](../../README.md) · [jays.website/tools](https://jays.website/tools/)

---

### Quick Run 🚀

```bash
# Preview what would be cleared (safe — no changes)
curl -fsSL https://raw.githubusercontent.com/JaysWebDev/dev-tools/main/system/automated-cleanup/weekly_cache_cleanup.sh | bash -s -- --dry-run

# Run it
curl -fsSL https://raw.githubusercontent.com/JaysWebDev/dev-tools/main/system/automated-cleanup/weekly_cache_cleanup.sh | bash
```

---

## Scripts

### `backup_retention_manager.sh`
Enforces retention policies on backup directories. Keeps the last N backups per category and removes older ones. Logs all actions with timestamps.

```bash
# Add to cron (runs daily at 3 AM):
0 3 * * * /path/to/backup_retention_manager.sh
```

### `weekly_cache_cleanup.sh`
Clears Python bytecode (`__pycache__`, `.pyc`), browser cache fragments, and temp files on a safe, non-destructive basis.

```bash
# Add to cron (runs Sunday at 2 AM):
0 2 * * 0 /path/to/weekly_cache_cleanup.sh
```

### `monthly_backup_check.sh`
Verifies that monthly backups exist and are non-empty. Alerts (stdout/log) if missing.

## Logs

Each script appends to its own log file alongside the script. Check `*.log` for history.
