#!/bin/bash
# Weekly Cache Cleanup — machine-aware, safe
# Usage: bash weekly_cache_cleanup.sh [--dry-run]

DRY_RUN=false
[[ "$1" == "--dry-run" ]] && DRY_RUN=true

USER_HOME="${HOME:-/home/$(whoami)}"
LOG_DIR="$USER_HOME/.local/share/dev-tools/logs"
LOG_FILE="$LOG_DIR/weekly_cleanup_$(date +%Y%m%d).log"
mkdir -p "$LOG_DIR"

run() {
  if $DRY_RUN; then echo "  [DRY-RUN] $*"; else eval "$@" 2>/dev/null || true; fi
}

log() { echo "$1" | tee -a "$LOG_FILE"; }

log "━━━ Cache Cleanup — $(date) ━━━"
$DRY_RUN && log "*** DRY RUN — no files will be deleted ***"

FREED=0

# Python bytecode
log ""
log "Python bytecode (.pyc / __pycache__)..."
PYC_COUNT=$(find "$USER_HOME" -name "*.pyc" -not -path "*/node_modules/*" 2>/dev/null | wc -l)
PYC_SIZE=$(find "$USER_HOME" -name "*.pyc" -not -path "*/node_modules/*" 2>/dev/null | xargs du -sc 2>/dev/null | tail -1 | cut -f1)
run "find '$USER_HOME' -name '*.pyc' -not -path '*/node_modules/*' -delete"
run "find '$USER_HOME' -name '__pycache__' -type d -not -path '*/node_modules/*' -exec rm -rf {} +"
log "  Removed $PYC_COUNT .pyc files (~${PYC_SIZE}KB)"

# pip cache
if command -v pip3 &>/dev/null; then
  log ""
  log "pip cache..."
  PIP_SIZE=$(pip3 cache info 2>/dev/null | grep "Cache size" | grep -oP '[0-9.]+[A-Za-z]+' | head -1 || echo "unknown")
  run "pip3 cache purge"
  log "  Cleared pip cache ($PIP_SIZE)"
fi

# npm cache
if command -v npm &>/dev/null; then
  log ""
  log "npm cache..."
  NPM_SIZE=$(npm cache verify 2>/dev/null | grep "Content verified" | head -1 || echo "")
  run "npm cache clean --force"
  log "  Cleared npm cache"
fi

# Browser caches (snap-based — safe to clear)
log ""
log "Browser caches (snap)..."
for cache_dir in \
  "$USER_HOME/snap/brave"/*/Cache \
  "$USER_HOME/snap/chromium"/*/Cache \
  "$USER_HOME/snap/discord"/*/Cache \
  "$USER_HOME/snap/slack"/*/Cache; do
  [ -d "$cache_dir" ] || continue
  SIZE=$(du -sh "$cache_dir" 2>/dev/null | cut -f1)
  run "rm -rf '$cache_dir'"
  log "  Cleared $cache_dir ($SIZE)"
done

# System .cache — only safe subdirs
log ""
log "User .cache (safe subdirs)..."
SAFE_CACHES=(mesa_shader_cache fontconfig thumbnails pip)
for subdir in "${SAFE_CACHES[@]}"; do
  cache_path="$USER_HOME/.cache/$subdir"
  [ -d "$cache_path" ] || continue
  SIZE=$(du -sh "$cache_path" 2>/dev/null | cut -f1)
  run "rm -rf '$cache_path'"
  log "  Cleared ~/.cache/$subdir ($SIZE)"
done

# Trash
log ""
log "Trash..."
TRASH="$USER_HOME/.local/share/Trash/files"
if [ -d "$TRASH" ] && [ "$(ls -A "$TRASH" 2>/dev/null)" ]; then
  SIZE=$(du -sh "$TRASH" 2>/dev/null | cut -f1)
  run "rm -rf '$TRASH'/* '$USER_HOME/.local/share/Trash/info'/*"
  log "  Emptied trash ($SIZE)"
else
  log "  Trash already empty"
fi

# Apt cache (only if root or sudo available)
if [[ "$UID" -eq 0 ]] || sudo -n true 2>/dev/null; then
  log ""
  log "APT package cache..."
  APT_SIZE=$(du -sh /var/cache/apt/archives 2>/dev/null | cut -f1)
  run "apt-get clean"
  log "  Cleared APT cache ($APT_SIZE)"
fi

# Summary
CACHE_AFTER=$(du -sh "$USER_HOME/.cache" 2>/dev/null | cut -f1)
log ""
log "━━━ Done — $(date) ━━━"
log "  ~/.cache now: $CACHE_AFTER"
log "  Log: $LOG_FILE"
$DRY_RUN && log "  *** Dry run complete — nothing was actually deleted ***"
