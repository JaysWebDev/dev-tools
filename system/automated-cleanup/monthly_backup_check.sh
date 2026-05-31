#!/bin/bash
# Monthly Backup Retention Check
# Runs first day of month at 3 AM

LOG_FILE="/home/j/automated_cleanup/monthly_backup.log"

echo "🛡️  Monthly Backup Check - $(date)" | tee -a "$LOG_FILE"
echo "==============================" | tee -a "$LOG_FILE"

# Run backup retention manager
/home/j/automated_cleanup/backup_retention_manager.sh | tee -a "$LOG_FILE"

# Check for large accumulated files
echo "🔍 Checking for large files..." | tee -a "$LOG_FILE"
find /home/j -size +100M -type f 2>/dev/null | head -10 | tee -a "$LOG_FILE"

echo "✅ Monthly backup check complete - $(date)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
