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
