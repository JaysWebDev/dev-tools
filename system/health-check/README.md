# System Health Check

Quick bash script for a one-shot system status overview: memory, disk, load, temperature, and network connectivity.

## Usage

```bash
bash health_check.sh
```

## Output

```
=== QUICK SYSTEM HEALTH CHECK ===
Memory usage: ...
Disk usage: ...
System load: ...
Temperature: ...
Internet: OK
```

Requires `lm-sensors` for temperature (`sudo apt install lm-sensors`).
