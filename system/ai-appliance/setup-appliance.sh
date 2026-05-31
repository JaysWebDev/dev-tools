#!/usr/bin/env bash
# =============================================================================
# setup-appliance.sh  —  v1 "Bootstrapper" — Run ONCE on first boot
# Stack: Ollama + Qwen2.5-1.5B + Open WebUI + Claude Code CLI
# Claude Code stays in v1 as boots-on-the-ground. Removed in v2.
# =============================================================================

# Don't use set -e — handle errors explicitly so we get useful output
set -uo pipefail

WHOAMI=$(whoami)
HOME_DIR=$(eval echo ~$WHOAMI)
LOG="$HOME_DIR/setup.log"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }
die() { log "ERROR: $*"; exit 1; }

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║      PRIVATE AI APPLIANCE v1 — First Boot Setup             ║"
echo "║  Internet needed once. Every boot after = offline.          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
log "Running as: $WHOAMI  |  Home: $HOME_DIR"

# ── [1/6] System packages ────────────────────────────────────────────────────
log "[1/6] Installing system packages..."
sudo apt-get update -qq 2>&1 | tail -1
sudo apt-get install -y curl python3-pip python3-venv git 2>&1 | tail -3
log "System packages done."

# ── [2/6] Node.js + Claude Code CLI ──────────────────────────────────────────
log "[2/6] Installing Node.js 20 + Claude Code..."
if ! command -v node &>/dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - 2>/dev/null
  sudo apt-get install -y nodejs 2>&1 | tail -2
fi
if ! command -v claude &>/dev/null; then
  sudo npm install -g @anthropic-ai/claude-code 2>&1 | tail -2
fi
log "Claude Code: $(claude --version 2>/dev/null || echo 'installed')"

# ── Claude credentials ────────────────────────────────────────────────────────
mkdir -p "$HOME_DIR/.claude"
for src in \
  "$(find /media /mnt /usb 2>/dev/null -name '.claude_credentials' 2>/dev/null | head -1)" \
  "/media/ventoy_data/.claude_credentials" \
  "/usb/.claude_credentials"; do
  if [[ -f "$src" ]]; then
    cp "$src" "$HOME_DIR/.claude/.credentials.json"
    chmod 600 "$HOME_DIR/.claude/.credentials.json"
    log "Claude credentials loaded from $src"
    break
  fi
done

# ── [3/6] Ollama ─────────────────────────────────────────────────────────────
log "[3/6] Installing Ollama..."
if ! command -v ollama &>/dev/null; then
  curl -fsSL https://ollama.com/install.sh | sudo sh 2>&1 | grep -E ">>>|Error" || true
fi

# Create systemd service manually (install script sometimes skips this in VMs)
if ! systemctl is-active --quiet ollama 2>/dev/null; then
  log "Creating Ollama systemd service..."
  sudo useradd -r -s /bin/false -U -m -d /usr/share/ollama ollama 2>/dev/null || true
  sudo usermod -a -G ollama "$WHOAMI" 2>/dev/null || true

  sudo tee /etc/systemd/system/ollama.service > /dev/null << 'SVC'
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

[Install]
WantedBy=default.target
SVC

  sudo systemctl daemon-reload
  sudo systemctl enable ollama
  sudo systemctl start ollama
  sleep 5
fi

if systemctl is-active --quiet ollama 2>/dev/null; then
  log "Ollama running ✓"
else
  die "Ollama failed to start — check: sudo systemctl status ollama"
fi

# ── [4/6] Pull model ──────────────────────────────────────────────────────────
log "[4/6] Pulling Qwen2.5 1.5B (~950MB)..."
if ! ollama list 2>/dev/null | grep -q "qwen2.5:1.5b"; then
  ollama pull qwen2.5:1.5b
fi
log "Model ready ✓"

# ── [5/6] Open WebUI ─────────────────────────────────────────────────────────
log "[5/6] Installing Open WebUI (venv)..."
VENV="$HOME_DIR/.venv/open-webui"
if [[ ! -f "$VENV/bin/open-webui" ]]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet open-webui 2>&1 | tail -2
fi
log "Open WebUI installed ✓"

mkdir -p "$HOME_DIR/.config/systemd/user"
cat > "$HOME_DIR/.config/systemd/user/open-webui.service" << SVC
[Unit]
Description=Open WebUI — Local AI Interface
After=network.target

[Service]
ExecStart=$VENV/bin/open-webui serve --port 8080
Restart=always
Environment=OLLAMA_BASE_URL=http://127.0.0.1:11434
Environment=ANONYMIZED_TELEMETRY=false
Environment=DO_NOT_TRACK=true
Environment=WEBUI_SECRET_KEY=local-only
Environment=WEBUI_AUTH=False

[Install]
WantedBy=default.target
SVC

systemctl --user daemon-reload
systemctl --user enable open-webui
systemctl --user start open-webui
sudo loginctl enable-linger "$WHOAMI"
log "Open WebUI started ✓"

# ── [6/6] Autostart + welcome ────────────────────────────────────────────────
log "[6/6] Configuring autostart..."
mkdir -p "$HOME_DIR/.config/autostart" "$HOME_DIR/Desktop"

cat > "$HOME_DIR/.config/autostart/ai-appliance-ui.desktop" << 'DESKTOP'
[Desktop Entry]
Type=Application
Name=AI Appliance
Exec=bash -c "sleep 8 && xdg-open http://localhost:8080"
X-GNOME-Autostart-enabled=true
DESKTOP

cat > "$HOME_DIR/Desktop/WELCOME.txt" << 'SPLASH'
╔══════════════════════════════════════════════════════════════╗
║     🔒  PRIVATE AI APPLIANCE v1  🔒                         ║
║                                                              ║
║  ✓ Local inference — Qwen2.5 1.5B via Ollama                ║
║  ✓ Open WebUI     → http://localhost:8080                    ║
║  ✓ Claude Code    → type 'claude' in terminal               ║
║  ✓ Kill switch    → unplug USB anytime                       ║
║                                                              ║
║  v1: Claude Code included as bootstrap engineer.            ║
║  v2: Fully autonomous, Claude removed.                       ║
╚══════════════════════════════════════════════════════════════╝
SPLASH

# ── Final check ───────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════"
log "Verifying stack..."
log "  Ollama:     $(systemctl is-active ollama 2>/dev/null)"
log "  Model:      $(ollama list 2>/dev/null | grep qwen || echo 'not found')"
log "  Open WebUI: $(systemctl --user is-active open-webui 2>/dev/null)"
log "  Claude:     $(claude --version 2>/dev/null)"
echo "════════════════════════════════════════════════════════════"
echo ""
log "✅ v1 Setup complete! Log saved to $LOG"

# Mark setup as done — prevents autostart from re-running
touch "$HOME_DIR/.ai-appliance-setup-done"
# Remove the first-boot launcher now that setup is complete
rm -f "$HOME_DIR/.config/autostart/ai-appliance-firstboot.desktop"

echo ""
echo "  Open WebUI  → http://localhost:8080"
echo "  Claude Code → claude"
echo "  Local model → ollama run qwen2.5:1.5b"
echo ""
