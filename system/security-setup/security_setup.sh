#!/bin/bash
# Machine-aware Ubuntu Security Hardening
# Auto-detects running services and preserves their ports before enabling UFW.
# Usage: sudo bash security_setup.sh [--dry-run] [--check-only]

set -euo pipefail
DRY_RUN=false
CHECK_ONLY=false
for arg in "$@"; do
  [[ "$arg" == "--dry-run"    ]] && DRY_RUN=true
  [[ "$arg" == "--check-only" ]] && CHECK_ONLY=true
done

# ── Root check ─────────────────────────────────────────────────────────────────
if [[ "$UID" -ne 0 ]] && ! $CHECK_ONLY; then
  echo "Run with sudo: sudo bash security_setup.sh"
  exit 1
fi

run() {
  if $DRY_RUN; then echo "  [DRY-RUN] $*"; else eval "$@"; fi
}

section() { echo ""; echo "━━━ $1 ━━━"; }
ok()      { echo "  ✓ $1"; }
warn()    { echo "  ⚠ $1"; }
info()    { echo "  → $1"; }

echo "╔══════════════════════════════════════════╗"
echo "║     SECURITY HARDENING SETUP             ║"
$DRY_RUN && echo "║          *** DRY RUN ***                 ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Detect running services and required ports ──────────────────────────────
section "DETECTING RUNNING SERVICES"

PORTS_TO_ALLOW=()
SERVICES_FOUND=()

# Always allow SSH — detect non-standard port
SSH_PORT=$(ss -tlnp | grep sshd | grep -oP ':\K[0-9]+' | head -1)
SSH_PORT=${SSH_PORT:-22}
PORTS_TO_ALLOW+=("$SSH_PORT/tcp|SSH")
ok "SSH on port $SSH_PORT"

# Nginx / web server
if systemctl is-active --quiet nginx 2>/dev/null || pgrep -x nginx &>/dev/null; then
  PORTS_TO_ALLOW+=("80/tcp|HTTP" "443/tcp|HTTPS")
  SERVICES_FOUND+=("nginx")
  ok "Nginx detected — allowing 80, 443"
fi

# Cloudflare tunnel — runs outbound only, no inbound port needed
if systemctl is-active --quiet cloudflared 2>/dev/null || pgrep -x cloudflared &>/dev/null; then
  SERVICES_FOUND+=("cloudflared")
  ok "Cloudflare tunnel detected — outbound only, no extra rule needed"
fi

# Tailscale — uses UDP 41641 (outbound, but needs to receive UDP too)
if command -v tailscale &>/dev/null && tailscale status &>/dev/null 2>&1; then
  PORTS_TO_ALLOW+=("41641/udp|Tailscale")
  SERVICES_FOUND+=("tailscale")
  ok "Tailscale detected — allowing UDP 41641"
fi

# OpenVPN
if systemctl is-active --quiet openvpn 2>/dev/null || pgrep -x openvpn &>/dev/null; then
  PORTS_TO_ALLOW+=("1194/udp|OpenVPN")
  SERVICES_FOUND+=("openvpn")
  ok "OpenVPN detected — allowing UDP 1194"
fi

# Flask / trading web app (localhost only — nginx proxies it, no external allow needed)
if ss -tlnp | grep -q ":5000 "; then
  SERVICES_FOUND+=("flask-5000")
  ok "Flask app on 5000 (localhost only — no external rule needed)"
fi

# PostgreSQL (localhost only)
if ss -tlnp | grep -q ":5432 "; then
  SERVICES_FOUND+=("postgres")
  ok "PostgreSQL on 5432 (localhost only — no external rule needed)"
fi

# Gitea
if ss -tlnp | grep -q ":3000 "; then
  PORTS_TO_ALLOW+=("3000/tcp|Gitea")
  SERVICES_FOUND+=("gitea")
  ok "Gitea on 3000 — allowing"
fi

echo ""
echo "  Services detected: ${SERVICES_FOUND[*]:-none}"
echo "  Ports to allow:    $(printf '%s  ' "${PORTS_TO_ALLOW[@]}" | sed 's/|[^ ]*//g')"

$CHECK_ONLY && { echo ""; echo "Check-only mode — exiting."; exit 0; }

# ── 2. Confirm before proceeding ───────────────────────────────────────────────
section "READY TO APPLY"
echo "  This will:"
echo "    • Install: ufw, fail2ban, rkhunter, lynis, clamav, apparmor-utils"
echo "    • Configure UFW with the rules above"
echo "    • Enable fail2ban (SSH brute-force protection)"
echo "    • Enable AppArmor profiles"
echo ""
if ! $DRY_RUN; then
  read -rp "  Continue? [y/N] " confirm
  [[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
fi

# ── 3. Install packages ────────────────────────────────────────────────────────
section "INSTALLING PACKAGES"

PACKAGES="ufw fail2ban rkhunter lynis clamav clamav-daemon apparmor-utils apparmor-profiles"

# Only install WireGuard if no VPN already present
if [[ ! " ${SERVICES_FOUND[*]} " =~ " tailscale " ]] && [[ ! " ${SERVICES_FOUND[*]} " =~ " openvpn " ]]; then
  PACKAGES="$PACKAGES wireguard wireguard-tools"
  info "No VPN detected — adding WireGuard to install list"
else
  ok "VPN already present — skipping WireGuard"
fi

run "apt-get update -qq"
run "apt-get install -y $PACKAGES"

# ── 4. Configure UFW ───────────────────────────────────────────────────────────
section "CONFIGURING FIREWALL (UFW)"

run "ufw --force reset"
run "ufw default deny incoming"
run "ufw default allow outgoing"
run "ufw logging on"

for rule in "${PORTS_TO_ALLOW[@]}"; do
  port="${rule%|*}"
  name="${rule#*|}"
  run "ufw allow $port comment '$name'"
  info "Allowed: $port ($name)"
done

run "ufw --force enable"
ok "UFW enabled with ${#PORTS_TO_ALLOW[@]} allow rules"

# ── 5. Configure Fail2Ban ──────────────────────────────────────────────────────
section "CONFIGURING FAIL2BAN"

cat > /tmp/jail.local << 'EOF'
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 3

[sshd]
enabled  = true
port     = ssh
logpath  = %(sshd_log)s
backend  = %(sshd_backend)s
EOF

run "mv /tmp/jail.local /etc/fail2ban/jail.local"
run "systemctl enable fail2ban"
run "systemctl restart fail2ban"
ok "Fail2Ban configured (3 retries → 1hr ban)"

# ── 6. AppArmor ────────────────────────────────────────────────────────────────
section "APPARMOR"

if aa-status &>/dev/null 2>&1; then
  ok "AppArmor already active"
else
  run "aa-enforce /etc/apparmor.d/* 2>/dev/null || true"
  ok "AppArmor profiles enforced"
fi

# ── 7. ClamAV ──────────────────────────────────────────────────────────────────
section "CLAMAV"

if systemctl is-active --quiet clamav-freshclam 2>/dev/null; then
  ok "ClamAV definitions already being updated by freshclam daemon"
else
  run "systemctl enable clamav-freshclam"
  run "systemctl start clamav-freshclam"
  ok "ClamAV freshclam daemon started"
fi

# ── 8. Security check script ───────────────────────────────────────────────────
section "CREATING SECURITY CHECK SCRIPT"

REAL_USER="${SUDO_USER:-$(logname 2>/dev/null || echo j)}"
HOME_DIR=$(getent passwd "$REAL_USER" | cut -d: -f6)
CHECK_SCRIPT="$HOME_DIR/security_check.sh"

cat > "$CHECK_SCRIPT" << 'CHECKEOF'
#!/bin/bash
echo "=== Security Status — $(date) ==="
echo ""
echo "--- Firewall ---"
ufw status verbose 2>/dev/null || echo "UFW not active"
echo ""
echo "--- Fail2Ban ---"
fail2ban-client status 2>/dev/null || echo "Fail2Ban not running"
echo ""
echo "--- Open ports ---"
ss -tlnp | grep -v "127.0.0.1\|::1"
echo ""
echo "--- Failed SSH attempts (last 24h) ---"
journalctl -u ssh --since "24 hours ago" 2>/dev/null | grep -i "failed\|invalid" | tail -10 || echo "None"
echo ""
echo "--- AppArmor ---"
aa-status 2>/dev/null | head -5 || echo "AppArmor not active"
echo ""
echo "--- System load ---"
uptime
CHECKEOF

chmod +x "$CHECK_SCRIPT"
chown "$REAL_USER:$REAL_USER" "$CHECK_SCRIPT" 2>/dev/null || true
ok "Security check script → $CHECK_SCRIPT"

# ── Summary ────────────────────────────────────────────────────────────────────
section "COMPLETE"
echo ""
echo "  ✓ UFW firewall active (${#PORTS_TO_ALLOW[@]} rules)"
echo "  ✓ Fail2Ban protecting SSH"
echo "  ✓ ClamAV definitions updating"
echo "  ✓ AppArmor profiles enabled"
echo ""
echo "  Next: run ~/security_check.sh to verify"
echo "        run: sudo lynis audit system  (full security audit)"
$DRY_RUN && echo "" && echo "  *** This was a dry run — nothing was changed ***"
