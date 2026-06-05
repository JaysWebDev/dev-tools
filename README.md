# dev-tools 🛠️

A collection of practical tools built and used in production — system administration, network monitoring, app utilities, and local AI infrastructure.

All tools are self-contained with their own README and no external dependencies beyond what's documented.
Browse the live catalog at [jays.website/tools](https://jays.website/tools/).

---

## System 🖥️

| Tool | Description |
|------|-------------|
| [health-check](system/health-check/) | Machine-aware health snapshot — detects running services, checks CPU load, temps, disk, and network. Clean ✓/⚠/✗ summary in under 3 seconds. |
| [diagnostics](system/diagnostics/) | Comprehensive read-only system audit — hardware, disk health, open ports, security posture, journal errors, pending updates. Saves timestamped log. |
| [security-setup](system/security-setup/) | One-shot Ubuntu security baseline — auto-detects services before enabling UFW (no lockouts), configures Fail2Ban, supports `--dry-run` and `--check-only`. |
| [automated-cleanup](system/automated-cleanup/) | Clears Python bytecode, pip/npm caches, snap browser caches, and user trash. Uses `$HOME` — no hardcoded paths. Safe to cron. |
| [ai-appliance](system/ai-appliance/) | One-command local AI stack: Ollama + Qwen2.5-1.5B + Open WebUI as a systemd service. No cloud, no subscriptions. |
| [homemind](system/homemind/) | FastAPI inference server for a Raspberry Pi 4. Offline-first local LLM with streaming responses and a web chat UI. |
| [usb-recovery](system/usb-recovery/) | Field-tested walkthrough for recovering headless Linux servers — Alpine rescue USB, SSH-over-network chroot, GRUB repair, netplan fix. No monitor needed. |

## App Development 🧰

| Tool | Description |
|------|-------------|
| [wifi-scanner](app-development/wifi-scanner/) | Discovers all devices on your subnet — IP, MAC, manufacturer, and government security flagging (NDAA §889, FCC Covered List). Speed monitor included. |
| [web-note-extractor](app-development/web-note-extractor/) | Chrome extension — saves any webpage as clean text or PDF with one click. Auto-scrolls, strips nav/ads, smart filename from page title + date. |
| [video-saver](app-development/video-saver/) | Chrome extension that intercepts HLS/MP4/WebM video streams and saves them locally. One-click toggle from the popup. |
| [duplicate-detector](app-development/duplicate-detector/) | Recursively scans for duplicate files by MD5 hash. Size-first grouping for speed. Reports wasted space ranked by group. Optional JSON output. |
| [file-organizer](app-development/file-organizer/) | Categorizes files by extension, strips EXIF/metadata before moving using exiftool. Confirm prompt before any changes — no surprises. |
| [scraper-lab](app-development/scraper-lab/) | Modular web scraping toolkit with pluggable cleaning engines — phone, address, email, URL normalization. Generates quality reports per field. |

---

Each tool folder is self-contained — clone just the subfolder you need, or the whole repo.
