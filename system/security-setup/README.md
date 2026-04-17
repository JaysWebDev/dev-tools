# Security Setup & Check

Two scripts for Linux system hardening and ongoing security monitoring.

## Scripts

### `security_check.sh` — Status snapshot
Prints current state of: UFW firewall, Fail2Ban, listening ports, recent failed SSH attempts, AppArmor, system load, and memory.

```bash
bash security_check.sh
```

### `security_setup.sh` — Initial hardening
Applies baseline security configuration to a fresh Ubuntu system.

```bash
sudo bash security_setup.sh
```

Run `security_check.sh` after setup to verify everything is active.
