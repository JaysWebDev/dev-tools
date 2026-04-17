#!/bin/bash

echo "=== Ubuntu Security Enhancement Script ==="
echo "Run this script with: sudo bash security_setup.sh"
echo ""

# Check if running as root
if [ "$UID" -ne 0 ]; then
    echo "Please run with sudo: sudo bash security_setup.sh"
    exit 1
fi

echo "Installing security tools..."

# Install security packages
apt update
apt install -y \
    ufw \
    fail2ban \
    rkhunter \
    lynis \
    clamav \
    clamav-daemon \
    apparmor-profiles \
    apparmor-utils \
    wireguard \
    wireguard-tools \
    network-manager-wireguard-gnome

echo "Configuring firewall..."
# Configure UFW firewall
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw logging on
ufw --force enable

echo "Configuring Fail2Ban..."
# Configure fail2ban
systemctl enable fail2ban
systemctl start fail2ban

# Create fail2ban local config
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
backend = %(sshd_backend)s
EOF

systemctl restart fail2ban

echo "Configuring AppArmor..."
# Enable AppArmor profiles
aa-enforce /etc/apparmor.d/*

echo "Setting up ClamAV..."
# Update ClamAV virus definitions
freshclam

echo "Creating security monitoring script..."
cat > /home/j/security_check.sh << 'EOF'
#!/bin/bash
echo "=== Security Status Check ==="
echo "Date: $(date)"
echo ""

echo "=== Firewall Status ==="
ufw status verbose
echo ""

echo "=== Fail2Ban Status ==="
fail2ban-client status
echo ""

echo "=== Active Network Connections ==="
ss -tulpn | grep LISTEN
echo ""

echo "=== Recent Failed Login Attempts ==="
journalctl -u ssh -n 10 | grep -i failed || echo "No recent failed SSH attempts"
echo ""

echo "=== AppArmor Status ==="
aa-status | head -10
echo ""

echo "=== System Load ==="
uptime
echo ""

echo "=== Memory Usage ==="
free -h
EOF

chmod +x /home/j/security_check.sh
chown j:j /home/j/security_check.sh

echo ""
echo "=== Security Setup Complete! ==="
echo ""
echo "Next steps:"
echo "1. Run: ~/security_check.sh (to check status)"
echo "2. Configure VPN in Settings → Network → VPN"
echo "3. Consider running: sudo lynis audit system"
echo ""
echo "Installed security features:"
echo "✓ UFW Firewall (enabled)"
echo "✓ Fail2Ban (protects against brute force)"
echo "✓ ClamAV antivirus"
echo "✓ AppArmor security profiles"
echo "✓ WireGuard VPN support"
echo "✓ Security monitoring script"