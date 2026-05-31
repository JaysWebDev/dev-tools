# Automated Cleanup

Scheduled maintenance scripts for backup retention and system cache cleanup. Designed to run via cron on a Linux home server.

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
