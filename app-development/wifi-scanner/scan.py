#!/usr/bin/env python3
"""
WiFi Network Scanner
Scans a local subnet, resolves MACs to manufacturers, flags government-flagged devices.

Usage:
    sudo python3 scan.py
    sudo python3 scan.py --subnet 192.168.1.0/24 --output /tmp/devices.json

Requirements:
    nmap (sudo apt install nmap)
    oui.csv from https://standards-oui.ieee.org/oui/oui.csv
"""

import subprocess
import json
import re
import csv
import os
import socket
import argparse
from datetime import datetime

# ── US Government security-flagged manufacturers ────────────────────────────
# Sources: FCC Covered List, NDAA Section 889, CISA advisories, Microsoft Volt Typhoon report
SECURITY_FLAGS = {
    # FCC "Covered List" — banned from US federal networks
    'huawei':    ('HIGH',   'FCC Covered List — banned from US federal networks'),
    'zte':       ('HIGH',   'FCC Covered List — banned from US federal networks'),
    'hikvision': ('HIGH',   'FCC Covered List + NDAA §889 — Chinese surveillance'),
    'dahua':     ('HIGH',   'FCC Covered List + NDAA §889 — Chinese surveillance'),
    'hytera':    ('HIGH',   'FCC Covered List — banned from US federal networks'),
    # Active FCC investigation / state-actor association
    'tp-link':   ('MEDIUM', 'FCC/Commerce Dept investigation 2024; Volt Typhoon botnet used TP-Link routers'),
    'tplink':    ('MEDIUM', 'FCC/Commerce Dept investigation 2024; Volt Typhoon botnet used TP-Link routers'),
    # CISA advisories / known vulnerabilities
    'reolink':   ('MEDIUM', 'CISA advisory — Chinese manufacturer, unresolved CVEs'),
    'uniview':   ('MEDIUM', 'Chinese surveillance manufacturer — similar concerns to Hikvision/Dahua'),
    'foscam':    ('MEDIUM', 'CISA advisory — multiple critical CVEs, Chinese manufacturer'),
    'hanwha':    ('LOW',    'South Korean manufacturer — CISA advisories on camera products'),
    'ezviz':     ('MEDIUM', 'Hikvision subsidiary — inherits FCC Covered List concerns'),
}

DEFAULT_OUI_CSV     = os.path.join(os.path.dirname(__file__), 'oui.csv')
DEFAULT_HISTORY     = os.path.join(os.path.dirname(__file__), 'history.json')
DEFAULT_OUTPUT      = os.path.join(os.path.dirname(__file__), 'devices.json')


def check_security_flag(manufacturer):
    m = manufacturer.lower()
    for keyword, (level, reason) in SECURITY_FLAGS.items():
        if keyword in m:
            return {'level': level, 'reason': reason}
    return None


def load_oui(path):
    oui_map = {}
    try:
        with open(path, newline='', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if len(row) >= 3:
                    prefix = row[1].strip().upper()
                    org    = row[2].strip()
                    oui_map[prefix] = org
    except Exception as e:
        print(f"OUI load error: {e}")
    return oui_map


def lookup_manufacturer(mac, oui_map):
    if not mac:
        return "Unknown"
    prefix = mac.upper().replace(':', '').replace('-', '')[:6]
    return oui_map.get(prefix, "Unknown")


def run_nmap(subnet):
    try:
        result = subprocess.run(
            ["sudo", "nmap", "-sn", "--host-timeout", "3s", subnet],
            capture_output=True, text=True, timeout=60
        )
        return result.stdout
    except Exception as e:
        print(f"nmap error: {e}")
        return ""


def parse_nmap(output):
    devices = []
    current = {}
    for line in output.splitlines():
        m = re.match(r'Nmap scan report for (.+)', line)
        if m:
            if current:
                devices.append(current)
            info = m.group(1).strip()
            ip_match   = re.search(r'\(?([\d\.]+)\)?$', info)
            host_match = re.match(r'^([^\(]+)\s*\(', info)
            current = {
                'ip':       ip_match.group(1) if ip_match else info,
                'hostname': host_match.group(1).strip() if host_match else '',
                'mac':      '',
            }
        elif 'Host is up' in line:
            lat_match = re.search(r'\((.+) latency\)', line)
            current['latency'] = lat_match.group(1) if lat_match else ''
        elif 'MAC Address:' in line:
            mac_match = re.search(r'MAC Address: ([0-9A-Fa-f:]+)', line)
            if mac_match:
                current['mac'] = mac_match.group(1).upper()
    if current:
        devices.append(current)
    return devices


def get_mac_table():
    mac_table = {}
    try:
        result = subprocess.run(["ip", "neigh", "show"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 5 and re.match(r'[\da-f]{2}:', parts[4], re.I):
                mac_table[parts[0]] = parts[4].upper()
    except Exception as e:
        print(f"ARP error: {e}")
    return mac_table


def resolve_hostname(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except:
        return ''


def guess_device_type(manufacturer, hostname, ip, this_ip):
    m = manufacturer.lower()
    h = hostname.lower()
    if ip == this_ip:
        return 'this-pc'
    if any(x in m for x in ['apple', 'iphone', 'ipad']):
        return 'apple'
    if any(x in m for x in ['samsung', 'lg electronics', 'huawei', 'xiaomi', 'oneplus']):
        return 'mobile'
    if any(x in m for x in ['raspberry', 'raspberrypi']):
        return 'raspberry-pi'
    if any(x in m for x in ['amazon', 'ring', 'echo']):
        return 'amazon'
    if any(x in m for x in ['google', 'nest']):
        return 'google'
    if any(x in m for x in ['tp-link', 'tplink', 'netgear', 'asus', 'ubiquiti', 'eero', 'linksys']):
        return 'router'
    if any(x in m for x in ['intel', 'dell', 'hewlett', 'lenovo', 'acer', 'asus tek', 'gigabyte']):
        return 'computer'
    if any(x in m for x in ['espressif', 'tuya', 'shenzhen', 'realtek']):
        return 'iot'
    if any(x in m for x in ['sony', 'roku', 'nvidia', 'vizio']):
        return 'media'
    if any(x in h for x in ['phone', 'iphone', 'android', 'pixel']):
        return 'mobile'
    if any(x in h for x in ['router', 'gateway', 'ap-']):
        return 'router'
    return 'unknown'


def load_history(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}


def save_history(history, path):
    with open(path, 'w') as f:
        json.dump(history, f)


def main():
    parser = argparse.ArgumentParser(description='WiFi Network Scanner with security flagging')
    parser.add_argument('--subnet',   default='192.168.1.0/24', help='Subnet to scan (default: 192.168.1.0/24)')
    parser.add_argument('--this-ip',  default='',               help='Your machine IP (marks it in output)')
    parser.add_argument('--oui',      default=DEFAULT_OUI_CSV,  help='Path to oui.csv')
    parser.add_argument('--history',  default=DEFAULT_HISTORY,  help='Path to history JSON file')
    parser.add_argument('--output',   default=DEFAULT_OUTPUT,   help='Output JSON path')
    args = parser.parse_args()

    print(f"[{datetime.now():%H:%M:%S}] Scanning {args.subnet}...")

    oui_map   = load_oui(args.oui)
    print(f"  OUI database: {len(oui_map):,} entries")

    nmap_out  = run_nmap(args.subnet)
    devices   = parse_nmap(nmap_out)
    mac_table = get_mac_table()
    history   = load_history(args.history)
    now       = datetime.now().isoformat()

    enriched = []
    for d in devices:
        ip       = d['ip']
        mac      = d.get('mac') or mac_table.get(ip, '')
        hostname = d.get('hostname') or resolve_hostname(ip)
        mfr      = lookup_manufacturer(mac, oui_map) if mac else 'Unknown'
        dtype    = guess_device_type(mfr, hostname, ip, args.this_ip)

        if ip not in history:
            history[ip] = {'first_seen': now, 'mac': mac}
        history[ip]['last_seen'] = now
        if mac and not history[ip].get('mac'):
            history[ip]['mac'] = mac

        enriched.append({
            'ip':           ip,
            'mac':          mac or history[ip].get('mac', ''),
            'hostname':     hostname,
            'manufacturer': mfr,
            'device_type':  dtype,
            'latency':      d.get('latency', ''),
            'status':       'online',
            'first_seen':   history[ip].get('first_seen', now),
            'last_seen':    now,
            'security_flag': check_security_flag(mfr),
        })

    enriched.sort(key=lambda d: (
        0 if d['ip'] == args.this_ip else 1,
        list(map(int, d['ip'].split('.')))
    ))

    save_history(history, args.history)

    output = {
        'scan_time':    now,
        'subnet':       args.subnet,
        'total_online': len(enriched),
        'devices':      enriched,
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"  Found {len(enriched)} devices")
    print(f"  Saved → {args.output}")


if __name__ == '__main__':
    main()
