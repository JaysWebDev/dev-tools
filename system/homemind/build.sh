#!/usr/bin/env bash
# HomeMind build script — Raspberry Pi 4 (RAK Hotspot V2 / DietPi / ARM64)
# Run as root directly on the Pi after first boot: sudo bash build.sh
set -euo pipefail

INSTALL_DIR="/opt/homemind"
MODEL_DIR="$INSTALL_DIR/models"
VENV_DIR="$INSTALL_DIR/venv"
SERVICE_USER="homemind"
PORT=8080

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${GREEN}[homemind]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }
info() { echo -e "${CYAN}[info]${NC} $*"; }
die()  { echo -e "${RED}[error]${NC} $*" >&2; exit 1; }

[[ $EUID -ne 0 ]] && die "Run as root: sudo bash build.sh"
[[ "$(uname -m)" != "aarch64" ]] && warn "Not ARM64 — continuing, but performance will differ"

echo ""
echo "  ██╗  ██╗ ██████╗ ███╗   ███╗███████╗███╗   ███╗██╗███╗   ██╗██████╗ "
echo "  ██║  ██║██╔═══██╗████╗ ████║██╔════╝████╗ ████║██║████╗  ██║██╔══██╗"
echo "  ███████║██║   ██║██╔████╔██║█████╗  ██╔████╔██║██║██╔██╗ ██║██║  ██║"
echo "  ██╔══██║██║   ██║██║╚██╔╝██║██╔══╝  ██║╚██╔╝██║██║██║╚██╗██║██║  ██║"
echo "  ██║  ██║╚██████╔╝██║ ╚═╝ ██║███████╗██║ ╚═╝ ██║██║██║ ╚████║██████╔╝"
echo "  ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝ "
echo "  Local AI Appliance — RAK Hotspot V2 Edition"
echo ""

# ── System packages ───────────────────────────────────────────────────────────
log "Installing system packages..."
apt-get update -qq
apt-get install -y --no-install-recommends \
    python3 python3-venv python3-dev \
    cmake make g++ pkg-config \
    libopenblas-dev liblapack-dev \
    avahi-daemon avahi-utils libnss-mdns \
    wget curl ca-certificates \
    2>/dev/null
log "System packages installed."

# ── Users & directories ───────────────────────────────────────────────────────
id "$SERVICE_USER" &>/dev/null || useradd -r -s /usr/sbin/nologin -d "$INSTALL_DIR" "$SERVICE_USER"
mkdir -p "$INSTALL_DIR" "$MODEL_DIR" "$INSTALL_DIR/static"

# Copy application files (expected next to build.sh)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/main.py"    "$INSTALL_DIR/main.py"
cp "$SCRIPT_DIR/index.html" "$INSTALL_DIR/static/index.html"

# ── Python venv ───────────────────────────────────────────────────────────────
log "Creating Python virtual environment..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip wheel --quiet

# ── llama-cpp-python with OpenBLAS (ARM64 optimised) ─────────────────────────
log "Building llama-cpp-python with OpenBLAS (10–15 min on Pi 4, be patient)..."

# Probe for OpenCL (unlikely on Pi 4, but future-proof for Pi 5 + Hailo)
GPU_BUILD=false
if command -v clinfo &>/dev/null && clinfo 2>/dev/null | grep -q "Number of platforms"; then
    warn "OpenCL detected — attempting GPU-accelerated build..."
    if CMAKE_ARGS="-DLLAMA_CLBLAST=ON" \
       "$VENV_DIR/bin/pip" install llama-cpp-python \
           --no-binary llama-cpp-python --quiet 2>/dev/null; then
        GPU_BUILD=true
        log "GPU build succeeded."
    else
        warn "GPU build failed — falling back to CPU+OpenBLAS"
    fi
fi

if [[ "$GPU_BUILD" == "false" ]]; then
    CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" \
    "$VENV_DIR/bin/pip" install llama-cpp-python \
        --no-binary llama-cpp-python --quiet \
        || die "llama-cpp-python build failed. Check cmake and libopenblas-dev are installed."
fi

# ── Other Python deps ─────────────────────────────────────────────────────────
log "Installing Python dependencies..."
"$VENV_DIR/bin/pip" install \
    "fastapi>=0.110.0" \
    "uvicorn[standard]>=0.29.0" \
    "psutil>=5.9.0" \
    --quiet

# ── RAM detection → model download ───────────────────────────────────────────
TOTAL_RAM_KB=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
TOTAL_RAM_GB=$(( TOTAL_RAM_KB / 1024 / 1024 ))
info "Detected ${TOTAL_RAM_GB} GB RAM"

if   [[ $TOTAL_RAM_GB -ge 7 ]]; then
    MODEL_FILE="phi-3-mini-4k-instruct-q4.gguf"
    MODEL_URL="https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
    MODEL_LABEL="Phi-3 Mini 4K Q4 (~2.4 GB) — best for 8 GB Pi"
elif [[ $TOTAL_RAM_GB -ge 3 ]]; then
    MODEL_FILE="qwen2-1_5b-instruct-q4_k_m.gguf"
    MODEL_URL="https://huggingface.co/Qwen/Qwen2-1.5B-Instruct-GGUF/resolve/main/qwen2-1_5b-instruct-q4_k_m.gguf"
    MODEL_LABEL="Qwen2 1.5B Instruct Q4_K_M (~1.1 GB) — best for 4 GB Pi"
else
    MODEL_FILE="tinyllama-1.1b-chat-v1.0.q4_k_m.gguf"
    MODEL_URL="https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.q4_k_m.gguf"
    MODEL_LABEL="TinyLlama 1.1B Q4_K_M (~637 MB) — for low-RAM Pi"
fi

TARGET="$MODEL_DIR/$MODEL_FILE"
if [[ -f "$TARGET" ]]; then
    log "Model already present: $MODEL_LABEL — skipping download."
else
    log "Downloading: $MODEL_LABEL"
    info "(This is a one-time download. After this, HomeMind works 100% offline.)"
    wget --progress=bar:force:noscroll -O "$TARGET.tmp" "$MODEL_URL" \
        && mv "$TARGET.tmp" "$TARGET" \
        || { rm -f "$TARGET.tmp"; die "Model download failed. Check internet connection and retry."; }
    log "Model downloaded: $TARGET"
fi

# ── mDNS: avahi advertisement (homemind.local) ────────────────────────────────
log "Configuring mDNS — device will appear as homemind.local"
cat > /etc/avahi/services/homemind.service << 'AVAHI_EOF'
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">HomeMind on %h</name>
  <service>
    <type>_http._tcp</type>
    <port>8080</port>
    <txt-record>path=/</txt-record>
    <txt-record>description=Local AI Appliance — no cloud required</txt-record>
  </service>
</service-group>
AVAHI_EOF
systemctl enable --now avahi-daemon 2>/dev/null || true

# ── Permissions ───────────────────────────────────────────────────────────────
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR" "$MODEL_DIR"

# ── Systemd service ───────────────────────────────────────────────────────────
log "Installing systemd service..."
cat > /etc/systemd/system/homemind.service << EOF
[Unit]
Description=HomeMind Local AI Appliance
Documentation=https://github.com/openclaw/homemind
After=network.target avahi-daemon.service

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$VENV_DIR/bin/python -m uvicorn main:app --host 0.0.0.0 --port $PORT --loop uvloop
Restart=always
RestartSec=5
Environment=HOMEMIND_DIR=$INSTALL_DIR
Environment=HOMEMIND_PORT=$PORT
# Safety: if OOM killer hits, bring the service back up
OOMPolicy=restart
# Limit to 90% of available memory
MemoryMax=90%

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now homemind

# ── Final status ──────────────────────────────────────────────────────────────
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo ""
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log " HomeMind is running."
log ""
log "  Browser URL:  http://${LOCAL_IP}:${PORT}"
log "  mDNS URL:     http://homemind.local:${PORT}  (same LAN)"
log "  Model loaded: ${MODEL_LABEL}"
log "  Logs:         journalctl -u homemind -f"
log ""
log "  Tip: Add more models by dropping .gguf files"
log "  into ${MODEL_DIR} — they appear in the UI."
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
