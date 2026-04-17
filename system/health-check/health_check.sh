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
