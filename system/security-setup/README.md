# Security Hardening Setup 🛡️

One-shot security baseline for Ubuntu — auto-detects running services (nginx, Tailscale, OpenVPN, Gitea) before enabling UFW so nothing gets locked out. Configures Fail2Ban with SSH brute-force protection. Supports `--dry-run` and `--check-only` flags.

Part of [dev-tools](../../README.md) · [jays.website/tools](https://jays.website/tools/)

---

### 1. Scripts

| Script | Purpose |
|--------|---------|
| `security_setup.sh` | Initial hardening — run once on a new server |
| `security_check.sh` | Status snapshot — run anytime to verify posture |

### 2. Initial Hardening 🚀

```bash
# Preview what will change (safe — makes no changes)
sudo bash security_setup.sh --dry-run

# Apply the baseline
sudo bash security_setup.sh
```

What it does:
- Detects active services (nginx, tailscaled, openvpn, gitea, etc.) and opens their ports before enabling UFW
- Enables UFW with SSH allowed — no lockout risk
- Installs and configures Fail2Ban with SSH jail
- Sets reasonable SSH hardening defaults

### 3. Check Security Status

```bash
# Run directly — no install needed
curl -fsSL https://raw.githubusercontent.com/JaysWebDev/dev-tools/main/system/security-setup/security_check.sh | bash
```

Output covers:
```
UFW:       ✓  active (Status: active)
Fail2Ban:  ✓  running
AppArmor:  ✓  active
SSH:       ✓  listening on port 22
Failed logins (last 24h): 3
```

### 4. Flags ⚙️

| Flag | Description |
|------|-------------|
| `--dry-run` | Print all changes without applying anything |
| `--check-only` | Status snapshot only, no changes |

### 5. Recommended Flow

```bash
# 1. Check current state
bash security_check.sh

# 2. Preview the setup
sudo bash security_setup.sh --dry-run

# 3. Apply
sudo bash security_setup.sh

# 4. Verify
bash security_check.sh
```
