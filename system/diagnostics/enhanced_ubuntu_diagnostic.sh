#!/bin/bash

# Enhanced Ubuntu System Diagnostic and USB Backup Script
# Fixes mounting issues, creates USB backups, installs Claude Code

echo "=== Enhanced Ubuntu System Diagnostic and USB Backup Script ==="
echo "Starting comprehensive system analysis, USB backup, and setup..."
echo ""

# Enable error handling
set -e
trap 'echo "Script failed at line $LINENO"' ERR

# Global variables
USB_PATH=""
LOG_FILE="system_diagnostic_$(date +%Y%m%d_%H%M%S).log"

# Function to log output with timestamps
log_section() {
    echo ""
    echo "=================================================="
    echo "$(date '+%H:%M:%S') - $1"
    echo "=================================================="
}

# Function to fix mounting issues
fix_mounting_issues() {
    log_section "FIXING MOUNTING ISSUES"
    
    echo "Checking for stuck loop devices..."
    
    # Show current loop devices
    losetup -a
    
    # Check for busy loop devices
    if mount | grep -q loop1; then
        echo "Loop1 device is mounted, attempting to unmount..."
        sudo umount /dev/loop1 2>/dev/null || echo "Could not unmount loop1"
    fi
    
    # Force unmount any stuck devices
    for loop in /dev/loop*; do
        if [ -b "$loop" ]; then
            if lsof "$loop" >/dev/null 2>&1; then
                echo "Found processes using $loop, attempting force unmount..."
                sudo fuser -km "$loop" 2>/dev/null || true
                sudo umount -f "$loop" 2>/dev/null || true
            fi
        fi
    done
    
    # Clean up orphaned loop devices
    sudo losetup -D 2>/dev/null || true
    
    # Refresh device mappings
    sudo partprobe 2>/dev/null || true
    sudo udevadm trigger
    sudo udevadm settle
    
    echo "Mounting issues cleanup completed"
}

# Function to detect and setup USB drive
setup_usb_workspace() {
    log_section "SETTING UP USB WORKSPACE"
    
    # Look for USB drives
    echo "Scanning for USB drives..."
    
    # Check common USB mount points
    for mount_point in /media/ubuntu/* /mnt/* /media/*; do
        if [ -d "$mount_point" ] && mountpoint -q "$mount_point" 2>/dev/null; then
            # Check if it's writable and has reasonable free space
            if [ -w "$mount_point" ] && [ $(df "$mount_point" | awk 'NR==2 {print $4}') -gt 100000 ]; then
                USB_PATH="$mount_point"
                echo "Found suitable USB drive at: $USB_PATH"
                break
            fi
        fi
    done
    
    # If no mounted USB found, look for unmounted USB devices
    if [ -z "$USB_PATH" ]; then
        echo "No mounted USB found. Checking for unmounted USB devices..."
        
        # Look for USB storage devices
        for device in $(lsblk -lpno NAME,TYPE,TRAN | grep "part.*usb" | cut -d' ' -f1); do
            echo "Found USB device: $device"
            mount_point="/mnt/usb_backup"
            sudo mkdir -p "$mount_point"
            if sudo mount "$device" "$mount_point" 2>/dev/null; then
                USB_PATH="$mount_point"
                echo "Mounted USB at: $USB_PATH"
                break
            fi
        done
    fi
    
    if [ -n "$USB_PATH" ]; then
        # Create directory structure on USB
        echo "Creating backup directory structure..."
        sudo mkdir -p "$USB_PATH"/{logs,configs,scripts,backups,diagnostics}
        echo "USB workspace ready at: $USB_PATH"
    else
        echo "No suitable USB drive found. Backup features will be disabled."
        echo "Insert a USB drive and re-run if you want backup functionality."
    fi
}

# Function to backup important files to USB
backup_files_to_usb() {
    if [ -z "$USB_PATH" ] || [ ! -d "$USB_PATH" ]; then
        echo "USB not available for backup"
        return 1
    fi
    
    log_section "BACKING UP FILES TO USB"
    
    echo "Copying system configuration files..."
    
    # Backup system configs (safely)
    for config in /etc/fstab /etc/hosts /etc/network/interfaces /etc/resolv.conf; do
        if [ -f "$config" ]; then
            sudo cp "$config" "$USB_PATH/configs/" 2>/dev/null || echo "Could not backup $config"
        fi
    done
    
    # Backup user files (if not root)
    if [ "$USER" != "root" ] && [ -d "/home/$USER" ]; then
        echo "Backing up user configuration files..."
        mkdir -p "$USB_PATH/backups/user_configs"
        
        # Copy important user configs
        for user_config in .bashrc .profile .ssh/config .gitconfig; do
            if [ -f "/home/$USER/$user_config" ]; then
                cp "/home/$USER/$user_config" "$USB_PATH/backups/user_configs/" 2>/dev/null || true
            fi
        done
    fi
    
    # Save current script to USB
    if [ -f "$0" ]; then
        cp "$0" "$USB_PATH/scripts/diagnostic_script.sh"
        echo "Saved current script to USB"
    fi
    
    echo "File backup to USB completed"
}

# Function to copy useful scripts to USB
copy_scripts_to_usb() {
    if [ -z "$USB_PATH" ] || [ ! -d "$USB_PATH" ]; then
        return 1
    fi
    
    log_section "CREATING PORTABLE SCRIPTS ON USB"
    
    # Create bootloader repair script
    cat > "$USB_PATH/scripts/fix_bootloader.sh" << 'EOF'
#!/bin/bash
# Bootloader Repair Script
echo "Mounting system for bootloader repair..."

sudo mount /dev/sda2 /mnt
sudo mount /dev/sda1 /mnt/boot/efi
sudo mount --bind /dev /mnt/dev
sudo mount --bind /proc /mnt/proc
sudo mount --bind /sys /mnt/sys
sudo mount --bind /run /mnt/run

echo "Installing GRUB..."
sudo chroot /mnt grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=ubuntu
sudo chroot /mnt update-grub

echo "Creating EFI boot entry..."
sudo efibootmgr --create --disk /dev/sda --part 1 --loader '\EFI\ubuntu\grubx64.efi' --label 'Ubuntu'

echo "Cleaning up..."
sudo umount -R /mnt

echo "Bootloader repair completed"
EOF

    # Create system health check script
    cat > "$USB_PATH/scripts/health_check.sh" << 'EOF'
#!/bin/bash
# Quick System Health Check
echo "=== QUICK SYSTEM HEALTH CHECK ==="

echo "Memory usage:"
free -h

echo "Disk usage:"
df -h

echo "System load:"
uptime

echo "Temperature (if available):"
sensors 2>/dev/null || echo "lm-sensors not installed"

echo "Network connectivity:"
ping -c 3 8.8.8.8 >/dev/null && echo "Internet: OK" || echo "Internet: FAILED"

echo "Health check completed"
EOF

    # Create drive wipe script
    cat > "$USB_PATH/scripts/wipe_drive.sh" << 'EOF'
#!/bin/bash
# Drive Wipe Script - USE WITH EXTREME CAUTION
echo "WARNING: This script will completely wipe /dev/sda"
echo "Press Ctrl+C to cancel, or Enter to continue"
read

echo "Wiping drive..."
sudo wipefs -a /dev/sda
sudo dd if=/dev/zero of=/dev/sda bs=1M count=100
echo "Drive wipe completed"
EOF

    # Make scripts executable
    chmod +x "$USB_PATH/scripts"/*.sh
    
    echo "Portable scripts created on USB"
}

# Start main execution
log_section "STARTING ENHANCED DIAGNOSTIC"

# Fix mounting issues first
fix_mounting_issues

# Setup USB workspace
setup_usb_workspace

# Call the backup functions
backup_files_to_usb
copy_scripts_to_usb

# 1. SYSTEM INFORMATION  
log_section "SYSTEM INFORMATION"
echo "Hostname: $(hostname)"
echo "Current user: $(whoami)"
echo "Date: $(date)"
echo "Uptime: $(uptime)"
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"

# 2. HARDWARE INFORMATION
log_section "HARDWARE INFORMATION"
echo "CPU Information:"
lscpu | head -20

echo ""
echo "Memory Information:"
free -h

echo ""
echo "PCI Devices:"
lspci | head -10

echo ""
echo "USB Devices:"
lsusb

echo ""
echo "Block Devices:"
lsblk

# 3. DISK HEALTH
log_section "DISK HEALTH CHECK"
echo "Disk partitions:"
sudo fdisk -l /dev/sda 2>/dev/null || echo "Could not read /dev/sda"

echo ""
echo "Filesystem check:"
sudo fsck -N /dev/sda* 2>/dev/null || echo "Could not check filesystems"

echo ""
echo "Mount points:"
mount | grep -E "(sda|ext4|vfat)"

# 4. NETWORK DIAGNOSTICS
log_section "NETWORK DIAGNOSTICS"
echo "Network interfaces:"
ip addr show

echo ""
echo "Network routes:"
ip route show

echo ""
echo "DNS resolution test:"
nslookup google.com || echo "DNS resolution failed"

echo ""
echo "Internet connectivity test:"
ping -c 3 8.8.8.8 && echo "Internet: OK" || echo "Internet: FAILED"

# 5. PACKAGE MANAGEMENT
log_section "PACKAGE MANAGEMENT"
echo "APT sources:"
cat /etc/apt/sources.list | grep -v "^#" | head -5

echo ""
echo "Updating package list..."
sudo apt update 2>&1 | tail -10

# 6. CLAUDE CODE INSTALLATION
log_section "CLAUDE CODE INSTALLATION"
echo "Installing Node.js and Claude Code..."

# Install Node.js
if ! command -v node >/dev/null 2>&1; then
    echo "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
    sudo apt install -y nodejs
else
    echo "Node.js already installed: $(node --version)"
fi

# Install Claude Code
if ! command -v claude-code >/dev/null 2>&1; then
    echo "Installing Claude Code..."
    sudo npm install -g @anthropic-ai/claude-code || echo "Claude Code installation failed"
else
    echo "Claude Code already installed"
fi

# 7. SYSTEM SERVICES
log_section "SYSTEM SERVICES"
echo "Critical services status:"
systemctl status networking bluetooth ssh 2>/dev/null | grep -E "(Active:|Loaded:)" || echo "Could not check services"

# 8. SECURITY STATUS
log_section "SECURITY STATUS"
echo "Firewall status:"
sudo ufw status || echo "UFW not installed"

echo ""
echo "User accounts:"
cut -d: -f1 /etc/passwd | tail -10

echo ""
echo "Sudo privileges:"
sudo -l 2>/dev/null | head -5 || echo "Could not check sudo privileges"

# 9. PERFORMANCE METRICS
log_section "PERFORMANCE METRICS"
echo "System load average:"
cat /proc/loadavg

echo ""
echo "Memory usage:"
cat /proc/meminfo | head -10

echo ""
echo "Disk I/O stats:"
iostat 2>/dev/null || echo "iostat not available (install sysstat)"

# 10. SAVE RESULTS
log_section "SAVING RESULTS"

# Save to USB if available
if [ -n "$USB_PATH" ] && [ -d "$USB_PATH" ]; then
    echo "Saving diagnostic results to USB..."
    cp "$LOG_FILE" "$USB_PATH/logs/" 2>/dev/null || true
    
    # Save hardware info
    lshw -short > "$USB_PATH/diagnostics/hardware_summary.txt" 2>/dev/null || true
    dmesg > "$USB_PATH/logs/dmesg.log" 2>/dev/null || true
    
    echo "Results saved to USB at: $USB_PATH"
    echo "USB Contents:"
    ls -la "$USB_PATH"/{logs,configs,scripts,backups,diagnostics} 2>/dev/null || true
fi

# Final summary
log_section "DIAGNOSTIC SUMMARY"
echo "System diagnostic completed at: $(date)"
echo "Hostname: $(hostname)"
echo "Uptime: $(uptime -p 2>/dev/null || uptime)"

# Check if major issues were found
ERROR_COUNT=0

# Check disk health
if ! mount | grep -q "/dev/sda"; then
    echo "WARNING: Main disk not properly mounted"
    ((ERROR_COUNT++))
fi

# Check network
if ! ping -c 1 8.8.8.8 >/dev/null 2>&1; then
    echo "WARNING: No internet connectivity"
    ((ERROR_COUNT++))
fi

# Check available space
ROOT_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$ROOT_USAGE" -gt 90 ]; then
    echo "WARNING: Root filesystem >90% full"
    ((ERROR_COUNT++))
fi

if [ $ERROR_COUNT -eq 0 ]; then
    echo "✓ System appears healthy - no major issues detected"
else
    echo "⚠ Found $ERROR_COUNT potential issues - check warnings above"
fi

echo ""
echo "Next steps:"
echo "- Review the diagnostic output above"
echo "- Check USB drive for saved logs and repair scripts"
echo "- Run bootloader repair script if needed"
echo "- Use health check script for regular monitoring"

echo ""
echo "Script completed successfully!"