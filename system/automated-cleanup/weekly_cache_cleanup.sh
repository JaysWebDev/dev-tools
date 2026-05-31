#!/bin/bash
# Weekly Cache Cleanup - Safe automated cleanup
# Runs every Sunday at 2 AM

LOG_FILE="/home/j/automated_cleanup/weekly_cleanup.log"

echo "🧹 Weekly Cache Cleanup - $(date)" | tee -a "$LOG_FILE"
echo "=================================" | tee -a "$LOG_FILE"

# Clean Python bytecode
echo "Cleaning Python bytecode..." | tee -a "$LOG_FILE"
find /home/j -name "*.pyc" -delete 2>/dev/null
find /home/j -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# Clean browser caches (safe portions)
echo "Cleaning browser caches..." | tee -a "$LOG_FILE"
rm -rf /home/j/snap/discord/*/Cache 2>/dev/null
rm -rf /home/j/snap/brave/*/Cache 2>/dev/null

# Clean package manager caches
echo "Cleaning package caches..." | tee -a "$LOG_FILE"
pip cache purge >/dev/null 2>&1
npm cache clean --force >/dev/null 2>&1

# Clean specific safe cache directories
if [ -d "/home/j/.cache" ]; then
    rm -rf /home/j/.cache/mesa_shader_cache 2>/dev/null
    rm -rf /home/j/.cache/fontconfig 2>/dev/null
    rm -rf /home/j/.cache/pip 2>/dev/null
fi

# Log results
CACHE_SIZE=$(du -sh /home/j/.cache 2>/dev/null | cut -f1)
echo "Cache size after cleanup: $CACHE_SIZE" | tee -a "$LOG_FILE"
echo "✅ Weekly cleanup complete - $(date)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
