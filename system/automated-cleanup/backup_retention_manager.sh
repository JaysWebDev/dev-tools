#!/bin/bash
# Automated Backup Retention Manager
# Prevents backup accumulation by enforcing retention policies
# Generated: January 10, 2026

BACKUP_DIR="/media/j/Extreme SSD/_Backups"
LOG_FILE="/home/j/backup_retention.log"
MAX_SCANNER_BACKUPS=3

echo "🛡️  Backup Retention Manager - $(date)"
echo "=======================================" | tee -a "$LOG_FILE"

# Function to log with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    log_message "❌ Backup directory not found: $BACKUP_DIR"
    exit 1
fi

log_message "🔍 Checking scanner backup retention..."

# Get list of scanner backups sorted by date (newest first)
SCANNER_BACKUPS=($(ls -1t "$BACKUP_DIR" | grep "Complete_Scanners_" | head -20))
SCANNER_COUNT=${#SCANNER_BACKUPS[@]}

log_message "📊 Found $SCANNER_COUNT scanner backups"

if [ $SCANNER_COUNT -gt $MAX_SCANNER_BACKUPS ]; then
    log_message "⚠️  Excess scanner backups found ($SCANNER_COUNT > $MAX_SCANNER_BACKUPS)"

    # Keep only the newest MAX_SCANNER_BACKUPS
    BACKUPS_TO_REMOVE=()
    for (( i=$MAX_SCANNER_BACKUPS; i<$SCANNER_COUNT; i++ )); do
        BACKUPS_TO_REMOVE+=("${SCANNER_BACKUPS[$i]}")
    done

    log_message "🧹 Will remove ${#BACKUPS_TO_REMOVE[@]} old backups:"

    for backup in "${BACKUPS_TO_REMOVE[@]}"; do
        backup_path="$BACKUP_DIR/$backup"
        if [ -d "$backup_path" ]; then
            size=$(du -sh "$backup_path" 2>/dev/null | cut -f1)
            log_message "   Removing: $backup ($size)"
            rm -rf "$backup_path"
            log_message "   ✅ Removed: $backup"
        fi
    done

    log_message "✅ Scanner backup retention enforced"
else
    log_message "✅ Scanner backup count within limits ($SCANNER_COUNT <= $MAX_SCANNER_BACKUPS)"
fi

# Check cache accumulation
CACHE_SIZE=$(du -sh "/home/j/.cache" 2>/dev/null | cut -f1)
log_message "📊 Current cache size: $CACHE_SIZE"

# If cache is over 1GB, suggest cleanup
if [[ "$CACHE_SIZE" =~ [0-9]+\.?[0-9]*G ]] && [[ $(echo "$CACHE_SIZE" | grep -o '^[0-9]*') -gt 1 ]]; then
    log_message "⚠️  Large cache detected ($CACHE_SIZE > 1GB)"
    log_message "💡 Consider running: ./safe_cleanup_phase1.sh"
fi

# Summary report
log_message "📊 Storage Summary:"
df -h "/media/j/Extreme SSD" | tail -1 | awk -v date="$(date '+%Y-%m-%d %H:%M:%S')" '{print date " - SSD Usage: " $3 "/" $2 " (" $5 ") - Available: " $4}' | tee -a "$LOG_FILE"

df -h "/" | tail -1 | awk -v date="$(date '+%Y-%m-%d %H:%M:%S')" '{print date " - Home Usage: " $3 "/" $2 " (" $5 ") - Available: " $4}' | tee -a "$LOG_FILE"

log_message "✅ Backup retention check complete"
echo ""