# System Health Check 🩺

Machine-aware health snapshot — detects running services (nginx, Tailscale, Cloudflare, cron), checks CPU load, temps, disk usage, and network. Outputs a clean ✓/⚠/✗ summary in under 3 seconds.

Part of [dev-tools](../../README.md) · [jays.website/tools](https://jays.website/tools/)

---

### 1. Quick Run 🚀

```bash
# Run directly — no install needed
curl -fsSL https://raw.githubusercontent.com/JaysWebDev/dev-tools/main/system/health-check/health_check.sh | bash
```

Or clone and run locally:
```bash
git clone https://github.com/JaysWebDev/dev-tools.git
bash dev-tools/system/health-check/health_check.sh
```

### 2. Requirements

Temperature readings require `lm-sensors`:

```bash
sudo apt install lm-sensors
sudo sensors-detect --auto
```

No other dependencies — pure bash.

### 3. Example Output

```
=== SYSTEM HEALTH CHECK ===

Services
  ✓  nginx
  ✓  tailscaled
  ✓  cloudflared
  ✓  cron
  ⚠  redis-server  (not running)

CPU & Memory
  Load avg:  0.42 / 0.38 / 0.31
  Memory:    3.1 GB / 15.6 GB (20%)
  Temp:      48°C

Disk
  /         ✓  22% used
  /media/j  ✓  61% used

Network
  Gateway:  ✓  reachable (2ms)
  Internet: ✓  online
```

### 4. Customization ⚙️

Edit the `SERVICES` array near the top of the script to match your machine:

```bash
SERVICES=(nginx tailscaled cloudflared cron postgresql)
```

### 5. Schedule via Cron

```bash
# Run every morning at 8 AM, log output
0 8 * * * /path/to/health_check.sh >> /var/log/health_check.log 2>&1
```
