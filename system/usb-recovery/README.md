# 🔧 USB Recovery Toolkit

**Custom bootable USB to recover headless Linux servers with broken boot or network config. Auto-starts SSH on boot, chroots into the broken install, reinstalls GRUB, and fixes netplan — no monitor, no keyboard needed.**

Part of [dev-tools](../../README.md) · jays.website/tools/

---

## 1. Overview

This is a field-tested recovery process using Alpine Linux as the rescue environment. Built specifically for Ubuntu/Debian servers that can't boot — GRUB corruption, broken netplan, failed upgrades, or kernel mismatches. The entire recovery happens over SSH from another machine.

**When to use:**
- Server won't boot (GRUB missing or misconfigured)
- Network unreachable after an upgrade (broken netplan/interfaces)
- Filesystem corruption preventing normal boot
- Need to reset root password or recover data without booting the OS

---

## 2. What You Need

- USB drive (≥ 2GB)
- Alpine Linux ISO — [alpinelinux.org/downloads](https://alpinelinux.org/downloads/) (Standard, x86_64)
- Another machine with SSH access on the same network
- Physical access to the server to boot from USB once

---

## 3. Build the Recovery USB

```bash
# Linux (replace /dev/sdX with your USB device)
sudo dd if=alpine-standard-*.iso of=/dev/sdX bs=4M status=progress && sync
```

On macOS, use `diskutil unmountDisk /dev/diskN` first, then `dd` with `/dev/rdiskN`.

---

## 4. Configure Alpine to Auto-Start SSH

Boot the server from the USB. Alpine drops you to a root shell with no password.

```bash
# Run Alpine's setup wizard — only network and SSH matter
setup-alpine    # answer: keyboard=us, hostname=rescue, eth0=dhcp, timezone=skip

# Set a root password (needed for SSH login)
passwd

# Enable and start SSH
rc-service sshd start
rc-update add sshd

# Find the IP
ip addr show eth0
```

You can now SSH in from another machine: `ssh root@<rescue-ip>`

---

## 5. Identify and Mount the Broken Install

```bash
# List all block devices to find your system drive
lsblk -f

# Common layout: /dev/sda2 = root, /dev/sda1 = EFI/boot
# Mount root partition
mount /dev/sda2 /mnt

# Mount EFI/boot partition (if it exists separately)
mount /dev/sda1 /mnt/boot/efi   # EFI systems
# or
mount /dev/sda1 /mnt/boot       # Legacy BIOS

# Bind system directories for chroot
mount --bind /dev  /mnt/dev
mount --bind /proc /mnt/proc
mount --bind /sys  /mnt/sys
mount -t efivarfs efivarfs /mnt/sys/firmware/efi/efivars  # EFI only
```

---

## 6. Chroot and Repair

```bash
chroot /mnt /bin/bash

# Inside chroot — you're now operating on the broken install
```

### Fix GRUB (EFI system)

```bash
apt-get install --reinstall grub-efi-amd64
grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=ubuntu
update-grub
```

### Fix GRUB (Legacy BIOS)

```bash
apt-get install --reinstall grub-pc
grub-install /dev/sda
update-grub
```

### Fix Broken Netplan / Network Config

```bash
# Check what's there
cat /etc/netplan/*.yaml

# Common fix: recreate a working config
cat > /etc/netplan/00-installer-config.yaml << 'EOF'
network:
  version: 2
  ethernets:
    eth0:                        # change to your interface name (ip link)
      dhcp4: true
      optional: true
EOF

chmod 600 /etc/netplan/00-installer-config.yaml
netplan generate
```

### Fix Kernel / Initramfs

```bash
# If kernel was partially updated
apt-get -f install
update-initramfs -u -k all
```

---

## 7. Unmount and Reboot

```bash
# Exit chroot
exit

# Unmount cleanly
umount /mnt/sys/firmware/efi/efivars 2>/dev/null
umount /mnt/sys
umount /mnt/proc
umount /mnt/dev
umount /mnt/boot/efi 2>/dev/null
umount /mnt/boot 2>/dev/null
umount /mnt

# Reboot — remove USB when prompted or just let it boot to disk
reboot
```

---

## 8. Troubleshooting

**`chroot: /bin/bash: exec format error`** — Architecture mismatch. If rescuing an ARM machine (Raspberry Pi), use an ARM Alpine ISO, not x86_64.

**`grub-install: error: cannot find EFI directory`** — EFI partition not mounted. Check `ls /mnt/boot/efi` and re-run the mount command for EFI.

**`update-grub` shows no kernels found** — Kernel package is broken. Run `apt-get install linux-image-generic` inside chroot.

**SSH refuses connection on Alpine** — Run `rc-service sshd restart` and check `iptables -L` isn't blocking port 22.

**Can't identify root partition** — Use `blkid` or `fdisk -l /dev/sda` to list partitions and their filesystems.

---

Part of [dev-tools](../../README.md) · jays.website/tools/
