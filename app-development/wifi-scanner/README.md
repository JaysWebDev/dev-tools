# WiFi Network Scanner

Scans your local subnet with nmap, resolves MAC addresses to manufacturers via the IEEE OUI database, and flags devices from government-flagged manufacturers (FCC Covered List, NDAA §889, CISA advisories).

Also includes a network speed and latency monitor that tracks download/upload speeds and ping over time.

## Tools

### `scan.py` — Network device scanner
- Discovers all active devices on your subnet
- Resolves MAC → manufacturer using IEEE OUI database
- Flags HIGH/MEDIUM/LOW risk devices (Huawei, TP-Link, Hikvision, etc.)
- Tracks first/last seen history per device
- Outputs JSON for dashboards or further processing

### `speedtest.py` — Speed & latency monitor
- Tests gateway and internet latency (ping)
- Runs speedtest-cli for download/upload speeds
- Keeps rolling history (configurable window)
- Outputs JSON with latest result + history

## Requirements

```bash
sudo apt install nmap
pip install speedtest-cli
```

Download the IEEE OUI database:
```bash
curl -o oui.csv https://standards-oui.ieee.org/oui/oui.csv
```

## Usage

```bash
# Scan your network
sudo python3 scan.py --subnet 192.168.1.0/24 --this-ip 192.168.1.100

# Run speed test
python3 speedtest.py --gateway 192.168.1.1

# Custom output paths
sudo python3 scan.py --subnet 10.0.0.0/24 --output /var/www/html/devices.json
```

## Security Flag Sources

| Level  | Source |
|--------|--------|
| HIGH   | FCC Covered List, NDAA Section 889 |
| MEDIUM | FCC/Commerce Dept investigations, CISA advisories |
| LOW    | CISA product advisories |

Manufacturers currently flagged: Huawei, ZTE, Hikvision, Dahua, Hytera, TP-Link, Reolink, Uniview, Foscam, Hanwha, Ezviz.
