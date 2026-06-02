# Ubuntu System Diagnostic 🔬

Comprehensive read-only system audit — hardware, CPU/memory, disk health, network, open ports, security posture, recent journal errors, and pending package updates. Saves a timestamped log to `/tmp`.

Part of [dev-tools](../../README.md) · [jays.website/tools](https://jays.website/tools/)

---

### 1. Quick Run 🚀

```bash
# Run directly — no install needed
curl -fsSL https://raw.githubusercontent.com/JaysWebDev/dev-tools/main/system/diagnostics/enhanced_ubuntu_diagnostic.sh | bash
```

Or clone and run locally:
```bash
git clone https://github.com/JaysWebDev/dev-tools.git
bash dev-tools/system/diagnostics/enhanced_ubuntu_diagnostic.sh
```

### 2. What It Covers

| Section | Details |
|---------|---------|
| Hardware | CPU model, core count, architecture |
| Memory | Total, used, available, swap |
| Disk | All mounts, health status, loop device audit |
| Network | Active interfaces, IP addresses, default route |
| Open Ports | Listening services via `ss` |
| Security | UFW status, Fail2Ban, last failed SSH attempts |
| Logs | Last 20 journal errors or warnings |
| Updates | Pending package upgrades |

### 3. Output

All output is printed to stdout and saved to a timestamped file in `/tmp`:

```
/tmp/system_diagnostic_2026-06-01_08-30-00.log
```

The script is **read-only** — it inspects only, never modifies system state.

### 4. When to Use 🛠️

- Post-install baseline check
- Before a backup or upgrade
- Diagnosing mounting or loop device issues
- Quick security posture snapshot
