#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# HomeMind Factory Flash Script
# Flashes DietPi to a USB/SD, injects the HomeMind stack, and pre-configures
# it for first-boot on a Raspberry Pi 4 (RAK Hotspot V2).
#
# Usage:
#   sudo bash factory_flash.sh /dev/sdX
#
# Run this on your Linux PC (not on the Pi).
# The DietPi image is cached in ~/homemind-cache/ so subsequent flashes
# skip the download entirely.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
RPIOS_BASE="https://downloads.raspberrypi.com/raspios_lite_arm64/images"
RPIOS_DIR="raspios_lite_arm64-2025-12-04"
RPIOS_FILE="2025-12-04-raspios-trixie-arm64-lite.img.xz"
IMG_URL="${RPIOS_BASE}/${RPIOS_DIR}/${RPIOS_FILE}"
CACHE_DIR="${HOME}/homemind-cache"
IMG_XZ="${CACHE_DIR}/rpi-os-lite-arm64.img.xz"
IMG="${CACHE_DIR}/rpi-os-lite-arm64.img"
HOMEMIND_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
log()  { echo -e "${GREEN}[flash]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }
info() { echo -e "${CYAN}[info]${NC} $*"; }
die()  { echo -e "${RED}[error]${NC} $*" >&2; exit 1; }
step() { echo -e "\n${BOLD}── $* ──${NC}"; }

# ── Guards ────────────────────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && die "Run as root: sudo bash factory_flash.sh /dev/sdX"
[[ $# -lt 1 ]]    && die "Usage: sudo bash factory_flash.sh /dev/sdX"

TARGET="$1"
[[ ! -b "$TARGET" ]] && die "Not a block device: $TARGET"

# Safety: refuse to flash the boot drive
BOOT_DEV=$(lsblk -no PKNAME "$(findmnt -n -o SOURCE /)" 2>/dev/null | head -1)
[[ "$TARGET" == "/dev/$BOOT_DEV" || "$TARGET" == "/dev/${BOOT_DEV}p1" ]] && \
    die "REFUSING: $TARGET appears to be your boot drive (/dev/$BOOT_DEV)"

# Show what we're about to wipe
echo ""
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}  WARNING: ALL DATA ON $TARGET WILL BE PERMANENTLY ERASED${NC}"
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
lsblk -o NAME,SIZE,LABEL,MOUNTPOINT "$TARGET" 2>/dev/null || true
echo ""
read -rp "Type YES to confirm: " CONFIRM
[[ "$CONFIRM" != "YES" ]] && { echo "Aborted."; exit 0; }

# ── Dependencies ──────────────────────────────────────────────────────────────
step "Checking dependencies"
for cmd in wget xz dd lsblk; do
    command -v "$cmd" &>/dev/null || { apt-get install -y "$cmd" 2>/dev/null || die "Missing: $cmd"; }
done
log "All dependencies present."

# ── Download (cached) ─────────────────────────────────────────────────────────
step "DietPi image"
mkdir -p "$CACHE_DIR"

if [[ -f "$IMG" ]]; then
    log "Using cached image: $IMG"
else
    if [[ ! -f "$IMG_XZ" ]]; then
        log "Downloading Raspberry Pi OS Lite ARM64..."
        info "URL: $IMG_URL"
        info "Saving to: $IMG_XZ"
        wget --progress=bar:force:noscroll -O "${IMG_XZ}.tmp" "$IMG_URL" \
            && mv "${IMG_XZ}.tmp" "$IMG_XZ" \
            || { rm -f "${IMG_XZ}.tmp"; die "Download failed."; }
    else
        log "Compressed image already cached: $IMG_XZ"
    fi

    log "Decompressing image (this takes ~2 min)..."
    xz -dk "$IMG_XZ" -c > "$IMG" || die "Decompression failed."
    log "Image ready: $IMG  ($(du -h "$IMG" | cut -f1))"
fi

# ── Unmount target ────────────────────────────────────────────────────────────
step "Unmounting $TARGET"
# Nautilus/desktop auto-mounts USB drives — force lazy unmount of everything
for part in $(lsblk -lno NAME "$TARGET" | tail -n+2); do
    if grep -q "/dev/$part " /proc/mounts 2>/dev/null; then
        log "Unmounting /dev/$part (lazy)"
        umount -l "/dev/$part" 2>/dev/null || umount "/dev/$part" || true
    fi
done
sync

# ── Flash ─────────────────────────────────────────────────────────────────────
step "Flashing to $TARGET"
log "Writing image... (this takes 5–12 min depending on USB speed)"
dd if="$IMG" of="$TARGET" bs=4M status=progress conv=fsync
sync
log "Flash complete."

# Force kernel to see new partition table
# (partx is more reliable than partprobe when desktop auto-mounter is active)
partx -u "$TARGET" 2>/dev/null || partprobe "$TARGET" 2>/dev/null || true
sleep 3

# ── Mount partitions ──────────────────────────────────────────────────────────
step "Mounting partitions"
MOUNT_BOOT=$(mktemp -d)
MOUNT_ROOT=$(mktemp -d)

# DietPi RPi image: p1 = FAT32 boot, p2 = ext4 root
PART_BOOT="${TARGET}1"
PART_ROOT="${TARGET}2"

# Handle both /dev/sdX1 and /dev/mmcblkXp1 naming
[[ ! -b "$PART_BOOT" ]] && PART_BOOT="${TARGET}p1"
[[ ! -b "$PART_ROOT" ]] && PART_ROOT="${TARGET}p2"
[[ ! -b "$PART_BOOT" ]] && die "Cannot find boot partition on $TARGET"
[[ ! -b "$PART_ROOT" ]] && die "Cannot find root partition on $TARGET"

mount "$PART_BOOT" "$MOUNT_BOOT" || die "Failed to mount boot partition"
mount "$PART_ROOT" "$MOUNT_ROOT" || die "Failed to mount root partition"
log "Boot → $MOUNT_BOOT"
log "Root → $MOUNT_ROOT"

# ── Configure Raspberry Pi OS headless first-boot ─────────────────────────────
step "Configuring headless first-boot"

# Enable SSH on first boot
touch "$MOUNT_BOOT/ssh"

# Set default user (pi) with password 'homemind'
# openssl passwd -6 generates a SHA-512 hash
HASHED_PW=$(openssl passwd -6 "homemind" 2>/dev/null || echo "homemind")
echo "pi:${HASHED_PW}" > "$MOUNT_BOOT/userconf.txt"

# Set hostname to homemind
echo "homemind" > "$MOUNT_ROOT/etc/hostname"
sed -i 's/raspberrypi/homemind/g' "$MOUNT_ROOT/etc/hosts" 2>/dev/null || true

log "Headless SSH + user config written."

# ── Inject HomeMind files ─────────────────────────────────────────────────────
step "Injecting HomeMind files"
DEST="$MOUNT_ROOT/opt/homemind"
mkdir -p "$DEST/static" "$DEST/models"

cp "$HOMEMIND_SRC/main.py"          "$DEST/main.py"
cp "$HOMEMIND_SRC/index.html"       "$DEST/static/index.html"
cp "$HOMEMIND_SRC/homemind.service" "$DEST/homemind.service"
cp "$HOMEMIND_SRC/build.sh"         "$DEST/build.sh"
chmod +x "$DEST/build.sh"

# Drop a README so the Pi shows what to do after first boot
cat > "$DEST/FIRST_BOOT.txt" << 'README_EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 HomeMind — First Boot Setup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. SSH in:
     ssh root@homemind.local  (password: homemind)
   or find IP with: arp -a | grep -i raspberry

2. Run the installer:
     sudo bash /opt/homemind/build.sh

3. That's it. Opens at http://homemind.local:8080
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
README_EOF

log "Files injected into $DEST"
ls -lh "$DEST/"

# ── Unmount & sync ────────────────────────────────────────────────────────────
step "Finalising"
sync
umount "$MOUNT_BOOT"
umount "$MOUNT_ROOT"
rmdir "$MOUNT_BOOT" "$MOUNT_ROOT"
log "Unmounted cleanly."

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  USB is ready. Safe to remove.${NC}"
echo ""
echo -e "  ${BOLD}Next steps:${NC}"
echo -e "  1. Plug USB into your RAK Hotspot (or any Pi 4)"
echo -e "  2. Connect Pi to Ethernet + power on"
echo -e "  3. Wait ~60 sec for first boot"
echo -e "  4. SSH in:  ${CYAN}ssh pi@homemind.local${NC}  (password: homemind)"
echo -e "  5. Run:     ${CYAN}sudo bash /opt/homemind/build.sh${NC}"
echo -e "  6. Open:    ${CYAN}http://homemind.local:8080${NC}"
echo ""
echo -e "  ${BOLD}To flash another USB:${NC}"
echo -e "  ${CYAN}sudo bash factory_flash.sh /dev/sdY${NC}"
echo -e "  (Image is cached — no re-download needed)"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
