#!/bin/bash
# Ubuntu System Diagnostic — read-only, no destructive operations
# Usage: bash enhanced_ubuntu_diagnostic.sh [--brief]
# Safe to run on any Ubuntu/Debian system at any time.

BRIEF=false
[[ "$1" == "--brief" ]] && BRIEF=true

LOG_FILE="/tmp/diagnostic_$(hostname)_$(date +%Y%m%d_%H%M%S).txt"
exec > >(tee -a "$LOG_FILE") 2>&1

section() {
  echo ""
  echo "══════════════════════════════════════════"
  echo "  $1"
  echo "══════════════════════════════════════════"
}
ok()   { echo "  ✓ $1"; }
warn() { echo "  ⚠ $1"; }
fail() { echo "  ✗ $1"; }
info() { echo "  → $1"; }

echo "╔══════════════════════════════════════════╗"
echo "║     UBUNTU SYSTEM DIAGNOSTIC             ║"
echo "║  Host : $(hostname)"
echo "║  User : $(whoami)"
echo "║  Date : $(date '+%Y-%m-%d %H:%M:%S')"
echo "╚══════════════════════════════════════════╝"

ISSUES=0

# ── 1. System Info ─────────────────────────────────────────────────────────────
section "SYSTEM INFORMATION"
echo "  OS:       $(lsb_release -ds 2>/dev/null || cat /etc/os-release | grep PRETTY | cut -d= -f2 | tr -d '"')"
echo "  Kernel:   $(uname -r)"
echo "  Arch:     $(uname -m)"
echo "  Uptime:   $(uptime -p 2>/dev/null || uptime)"
echo "  Boot:     $(who -b 2>/dev/null | awk '{print $3,$4}' || echo 'unknown')"

# ── 2. Hardware ────────────────────────────────────────────────────────────────
section "HARDWARE"
echo "  --- CPU ---"
lscpu | grep -E "^Model name|^CPU\(s\)|^Thread|^Core" | sed 's/^/  /'
echo ""
echo "  --- Memory ---"
free -h | sed 's/^/  /'
echo ""
echo "  --- Block Devices ---"
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE | sed 's/^/  /'

# ── 3. Disk Health ─────────────────────────────────────────────────────────────
section "DISK HEALTH"
df -h | grep -E "^/dev" | while read -r fs size used avail pct mount; do
  pct_num=${pct/\%/}
  if [ "$pct_num" -ge 90 ] 2>/dev/null; then
    fail "$mount: $used/$size ($pct) — CRITICAL"
    ((ISSUES++)) || true
  elif [ "$pct_num" -ge 75 ] 2>/dev/null; then
    warn "$mount: $used/$size ($pct) — getting full"
  else
    ok "$mount: $used/$size ($pct)"
  fi
done

# inode usage
df -i | grep "^/dev" | while read -r fs inodes iused ifree ipct mount; do
  pct_num=${ipct/\%/}
  [ "$pct_num" -ge 80 ] 2>/dev/null && warn "Inodes low on $mount ($ipct used)"
done

# ── 4. Memory Analysis ─────────────────────────────────────────────────────────
section "MEMORY"
free -h | sed 's/^/  /'
SWAP_TOTAL=$(free | awk 'NR==3{print $2}')
SWAP_USED=$(free  | awk 'NR==3{print $3}')
if [ "$SWAP_TOTAL" -gt 0 ] 2>/dev/null; then
  PCT=$(( SWAP_USED * 100 / SWAP_TOTAL ))
  [ "$PCT" -gt 80 ] && warn "Swap $PCT% used — possible memory pressure" || ok "Swap $PCT% used"
fi

# ── 5. CPU & Load ──────────────────────────────────────────────────────────────
section "CPU & LOAD"
CORES=$(nproc)
LOAD=$(awk '{print $1}' /proc/loadavg)
echo "  Cores: $CORES  |  Load (1/5/15m): $(awk '{print $1,$2,$3}' /proc/loadavg)"
LOAD_PCT=$(echo "$LOAD $CORES" | awk '{printf "%d", ($1/$2)*100}')
[ "$LOAD_PCT" -gt 80 ] && warn "Load high (${LOAD_PCT}% of capacity)" && ((ISSUES++)) || true || ok "Load OK (${LOAD_PCT}%)"

$BRIEF || {
  echo ""
  echo "  --- Top 5 processes by CPU ---"
  ps aux --sort=-%cpu | awk 'NR>1 && NR<=6 {printf "  %-20s %5.1f%% CPU  %5.1f%% MEM\n", $11, $3, $4}'
  echo "  --- Top 5 processes by MEM ---"
  ps aux --sort=-%mem | awk 'NR>1 && NR<=6 {printf "  %-20s %5.1f%% MEM  %5.1f%% CPU\n", $11, $4, $3}'
}

# ── 6. Temperature ─────────────────────────────────────────────────────────────
section "TEMPERATURE"
if command -v sensors &>/dev/null; then
  sensors 2>/dev/null | grep -E "Core|Package|temp" | while read -r line; do
    temp=$(echo "$line" | grep -oP '[0-9]+\.[0-9]+(?=°C)' | head -1)
    [ -z "$temp" ] && continue
    if (( $(echo "$temp > 85" | bc -l 2>/dev/null) )); then
      fail "$line  ← HOT"
      ((ISSUES++)) || true
    elif (( $(echo "$temp > 70" | bc -l 2>/dev/null) )); then
      warn "$line  ← warm"
    else
      ok "$line"
    fi
  done
else
  info "lm-sensors not installed — run: sudo apt install lm-sensors && sudo sensors-detect"
fi

# ── 7. Network ─────────────────────────────────────────────────────────────────
section "NETWORK"
echo "  --- Interfaces ---"
ip -brief addr | sed 's/^/  /'
echo ""
echo "  --- Listening ports (external) ---"
ss -tlnp | grep -v "127.0.0.1\|::1\|Netid" | sed 's/^/  /'
echo ""
echo "  --- Connectivity ---"
ping -c 1 -W 2 8.8.8.8 &>/dev/null && ok "Internet (8.8.8.8)" || { fail "Internet unreachable"; ((ISSUES++)) || true; }
ping -c 1 -W 2 1.1.1.1 &>/dev/null && ok "Cloudflare (1.1.1.1)" || warn "Cloudflare unreachable"

# DNS
host google.com &>/dev/null && ok "DNS resolution" || { fail "DNS resolution failed"; ((ISSUES++)) || true; }

# Tailscale
command -v tailscale &>/dev/null && {
  TS=$(tailscale status 2>/dev/null | head -1)
  [ -n "$TS" ] && ok "Tailscale: $TS" || warn "Tailscale not connected"
}

# ── 8. Services ────────────────────────────────────────────────────────────────
section "SERVICES"
SERVICES=(ssh nginx cron fail2ban ufw cloudflared tailscaled postgresql gitea)
for svc in "${SERVICES[@]}"; do
  if systemctl list-units --all --type=service 2>/dev/null | grep -q "^.*${svc}"; then
    systemctl is-active --quiet "$svc" 2>/dev/null && ok "$svc" || warn "$svc is stopped"
  fi
done

# Detect unlisted listening services
echo ""
echo "  --- All listening processes ---"
ss -tlnp | awk 'NR>1{print "  ",$0}' | grep -v "^  $"

# ── 9. Security Posture ────────────────────────────────────────────────────────
section "SECURITY"

# UFW
if command -v ufw &>/dev/null; then
  UFW_STATUS=$(ufw status 2>/dev/null | head -1)
  [[ "$UFW_STATUS" == *"active"* ]] && ok "UFW: $UFW_STATUS" || warn "UFW: $UFW_STATUS"
else
  warn "UFW not installed"
fi

# Fail2ban
systemctl is-active --quiet fail2ban 2>/dev/null && ok "Fail2Ban active" || warn "Fail2Ban not running"

# AppArmor
aa-status &>/dev/null 2>&1 && ok "AppArmor active ($(aa-status 2>/dev/null | grep 'profiles are in enforce' | awk '{print $1}') enforced)" || warn "AppArmor not active"

# Unattended upgrades
dpkg -l unattended-upgrades &>/dev/null && ok "Unattended upgrades installed" || warn "Unattended upgrades not installed"

# Open SSH root login
grep -qE "^PermitRootLogin yes" /etc/ssh/sshd_config 2>/dev/null && warn "SSH root login enabled!" && ((ISSUES++)) || true
grep -qE "^PasswordAuthentication yes" /etc/ssh/sshd_config 2>/dev/null && warn "SSH password auth enabled (consider key-only)" || true

# ── 10. Logs — recent errors ───────────────────────────────────────────────────
section "RECENT ERRORS (last 2h)"
KERN_ERRS=$(journalctl -k --since "2 hours ago" -p err --no-pager 2>/dev/null | grep -c "." || echo 0)
SYS_ERRS=$(journalctl --since "2 hours ago" -p err --no-pager 2>/dev/null | grep -c "." || echo 0)

[ "$KERN_ERRS" -gt 0 ] && warn "$KERN_ERRS kernel error(s) in last 2h:" && \
  journalctl -k --since "2 hours ago" -p err --no-pager 2>/dev/null | tail -5 | sed 's/^/    /' || ok "No kernel errors"

[ "$SYS_ERRS" -gt 10 ] && warn "$SYS_ERRS system error(s) in last 2h (showing latest):" && \
  journalctl --since "2 hours ago" -p err --no-pager 2>/dev/null | tail -5 | sed 's/^/    /' || ok "System errors within normal range ($SYS_ERRS)"

# ── 11. Package updates ────────────────────────────────────────────────────────
$BRIEF || {
  section "PACKAGE UPDATES"
  UPDATES=$(apt list --upgradeable 2>/dev/null | grep -c upgradeable || echo 0)
  SECURITY=$(apt list --upgradeable 2>/dev/null | grep -c security || echo 0)
  [ "$SECURITY" -gt 0 ] && warn "$SECURITY security updates pending" && ((ISSUES++)) || true
  [ "$UPDATES" -gt 0 ]  && info "$UPDATES total updates available" || ok "System up to date"
}

# ── Summary ────────────────────────────────────────────────────────────────────
section "SUMMARY"
echo "  Host:    $(hostname)"
echo "  Date:    $(date)"
echo "  Log:     $LOG_FILE"
echo ""
if [ "$ISSUES" -eq 0 ]; then
  echo "  ✓ No issues detected — system appears healthy"
else
  echo "  ⚠ $ISSUES issue(s) found — review warnings above"
fi
echo ""
echo "  Tip: re-run with --brief for a condensed output"
echo "       share $LOG_FILE for remote diagnosis"
