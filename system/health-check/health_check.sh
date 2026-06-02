#!/bin/bash
# System Health Check — machine-aware, safe read-only
# Usage: bash health_check.sh [--json]

JSON_MODE=false
[[ "$1" == "--json" ]] && JSON_MODE=true

# ── Helpers ────────────────────────────────────────────────────────────────────
section() { echo ""; echo "━━━ $1 ━━━"; }
ok()      { echo "  ✓ $1"; }
warn()    { echo "  ⚠ $1"; }
fail()    { echo "  ✗ $1"; }

# ── Header ─────────────────────────────────────────────────────────────────────
echo "╔══════════════════════════════════════╗"
echo "║      SYSTEM HEALTH CHECK             ║"
echo "║  $(date '+%Y-%m-%d %H:%M:%S')        ║"
echo "╚══════════════════════════════════════╝"

# ── Memory ─────────────────────────────────────────────────────────────────────
section "MEMORY"
free -h | awk 'NR==1{print "  "$0} NR==2{
  split($4,a,/[A-Za-z]/); avail=a[1]; unit=substr($4,length(a[1])+1,1)
  print "  "$0
  if (unit=="G" && avail+0 < 0.5) print "  ⚠ Available memory low"
  else if (unit=="M" && avail+0 < 512) print "  ⚠ Available memory low (<512MB)"
  else print "  ✓ Memory OK"
}'
SWAP_USED=$(free | awk 'NR==3{if($2>0) printf "%.0f", $3/$2*100; else print 0}')
[ "$SWAP_USED" -gt 80 ] 2>/dev/null && warn "Swap usage high (${SWAP_USED}%)" || ok "Swap OK (${SWAP_USED}% used)"

# ── Disk ───────────────────────────────────────────────────────────────────────
section "DISK"
df -h | grep -E "^/dev|^tmpfs" | grep -v "tmpfs.*\/run\|tmpfs.*\/dev\|udev" | while read -r fs size used avail pct mount; do
  pct_num=${pct/\%/}
  if [ "$pct_num" -ge 90 ] 2>/dev/null; then
    echo "  ✗ $mount: $used/$size (${pct}) — CRITICAL"
  elif [ "$pct_num" -ge 75 ] 2>/dev/null; then
    echo "  ⚠ $mount: $used/$size (${pct}) — getting full"
  else
    echo "  ✓ $mount: $used/$size (${pct})"
  fi
done

# ── CPU / Load ─────────────────────────────────────────────────────────────────
section "CPU & LOAD"
CORES=$(nproc)
LOAD=$(cat /proc/loadavg | awk '{print $1}')
echo "  Cores: $CORES  |  Load avg: $(cat /proc/loadavg | awk '{print $1,$2,$3}')"
LOAD_INT=$(echo "$LOAD $CORES" | awk '{printf "%d", ($1/$2)*100}')
[ "$LOAD_INT" -gt 80 ] && warn "Load high (${LOAD_INT}% of core capacity)" || ok "Load OK (${LOAD_INT}% of core capacity)"

# ── Temperature ────────────────────────────────────────────────────────────────
section "TEMPERATURE"
if command -v sensors &>/dev/null; then
  sensors 2>/dev/null | grep -E "Core|Package|temp1" | while read -r line; do
    temp=$(echo "$line" | grep -oP '[0-9]+\.[0-9]+(?=°C)' | head -1)
    [ -n "$temp" ] && {
      [ "$(echo "$temp > 80" | bc -l 2>/dev/null)" = "1" ] && warn "$line" || ok "$line"
    }
  done
else
  echo "  (lm-sensors not installed)"
fi

# ── Services ───────────────────────────────────────────────────────────────────
section "SERVICES"
check_service() {
  local name=$1 display=${2:-$1}
  if systemctl is-active --quiet "$name" 2>/dev/null; then
    ok "$display active"
  elif systemctl list-units --all | grep -q "$name" 2>/dev/null; then
    fail "$display inactive"
  fi
}
check_service nginx "Nginx"
check_service "trading-web" "Trading Flask app"
check_service cloudflared "Cloudflare tunnel"
check_service tailscaled "Tailscale"
check_service fail2ban "Fail2Ban"
check_service cron "Cron"
check_service postgresql "PostgreSQL"
check_service gitea "Gitea"
check_service openvpn "OpenVPN"

# Count running cron jobs
CRON_JOBS=$(crontab -l 2>/dev/null | grep -v "^#\|^$" | wc -l)
ok "$CRON_JOBS active cron jobs"

# ── Network ────────────────────────────────────────────────────────────────────
section "NETWORK"
ping -c 1 -W 2 8.8.8.8 &>/dev/null && ok "Internet reachable" || fail "Internet unreachable"
ping -c 1 -W 2 1.1.1.1 &>/dev/null && ok "Cloudflare DNS reachable" || warn "Cloudflare DNS unreachable"

# Tailscale
if command -v tailscale &>/dev/null; then
  TS_STATUS=$(tailscale status 2>/dev/null | head -1)
  [ -n "$TS_STATUS" ] && ok "Tailscale: $TS_STATUS" || warn "Tailscale not connected"
fi

# Open external ports
OPEN_PORTS=$(ss -tlnp | grep -v "127.0.0.1\|::1\|::$" | awk 'NR>1{print $4}' | grep -oP ':\K[0-9]+' | sort -u | tr '\n' ' ')
echo "  Public listening ports: ${OPEN_PORTS:-none}"

# ── Process anomalies ──────────────────────────────────────────────────────────
section "PROCESSES"
CPU_HOG=$(ps aux --sort=-%cpu | awk 'NR==2{printf "%s (%.1f%% CPU)", $11, $3}')
MEM_HOG=$(ps aux --sort=-%mem | awk 'NR==2{printf "%s (%.1f%% MEM)", $11, $4}')
echo "  Top CPU: $CPU_HOG"
echo "  Top MEM: $MEM_HOG"
ZOMBIE=$(ps aux | awk '$8=="Z"' | wc -l)
[ "$ZOMBIE" -gt 0 ] && warn "$ZOMBIE zombie process(es)" || ok "No zombie processes"

# ── Recent errors ──────────────────────────────────────────────────────────────
section "RECENT ERRORS (last hour)"
KERN_ERRS=$(journalctl -k --since "1 hour ago" -p err 2>/dev/null | grep -v "^-- " | wc -l)
SYS_ERRS=$(journalctl --since "1 hour ago" -p err 2>/dev/null | grep -v "^-- " | wc -l)
[ "$KERN_ERRS" -gt 0 ] && warn "$KERN_ERRS kernel errors" || ok "No kernel errors"
[ "$SYS_ERRS" -gt 5 ] && warn "$SYS_ERRS system errors" || ok "System errors OK ($SYS_ERRS)"

# ── Summary ────────────────────────────────────────────────────────────────────
section "DONE"
echo "  Health check complete — $(date '+%H:%M:%S')"
