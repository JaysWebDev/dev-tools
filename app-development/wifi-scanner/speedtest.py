#!/usr/bin/env python3
"""
Network Speed & Latency Monitor
Tests gateway + internet latency and download/upload speed. Saves rolling history to JSON.

Usage:
    python3 speedtest.py
    python3 speedtest.py --gateway 192.168.1.1 --output results.json --history speedtest_history.json

Requirements:
    speedtest-cli (pip install speedtest-cli)
"""

import json
import subprocess
import re
import os
import argparse
from datetime import datetime

DEFAULT_OUTPUT  = os.path.join(os.path.dirname(__file__), 'speedtest.json')
DEFAULT_HISTORY = os.path.join(os.path.dirname(__file__), 'speedtest_history.json')
MAX_HISTORY     = 48  # 24 hours at 30-min intervals


def ping_latency(host, count=10):
    try:
        result = subprocess.run(
            ["ping", "-c", str(count), "-i", "0.2", "-W", "2", host],
            capture_output=True, text=True, timeout=30
        )
        for line in result.stdout.splitlines():
            if "rtt min" in line or "round-trip" in line:
                parts = line.split("=")[-1].strip().split("/")
                return {
                    "min":  round(float(parts[0]), 2),
                    "avg":  round(float(parts[1]), 2),
                    "max":  round(float(parts[2]), 2),
                    "loss": parse_loss(result.stdout),
                }
    except Exception as e:
        print(f"  Ping {host} failed: {e}")
    return {"min": None, "avg": None, "max": None, "loss": 100}


def parse_loss(output):
    for line in output.splitlines():
        if "packet loss" in line:
            m = re.search(r'(\d+(?:\.\d+)?)% packet loss', line)
            if m:
                return float(m.group(1))
    return 0


def run_speedtest():
    try:
        print("  Running speed test (~20s)...")
        result = subprocess.run(
            ["speedtest-cli", "--json"],
            capture_output=True, text=True, timeout=90
        )
        data   = json.loads(result.stdout)
        server = data.get("server", {}).get("sponsor", "") + " — " + data.get("server", {}).get("name", "")
        return {
            "download_mbps": round(data["download"] / 1_000_000, 1),
            "upload_mbps":   round(data["upload"]   / 1_000_000, 1),
            "ping_ms":       round(data["ping"], 1),
            "server":        server.strip(" —"),
        }
    except Exception as e:
        print(f"  Speed test failed: {e}")
        return {"download_mbps": None, "upload_mbps": None, "ping_ms": None, "server": ""}


def load_history(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return []


def main():
    parser = argparse.ArgumentParser(description='Network speed and latency monitor')
    parser.add_argument('--gateway',  default='192.168.1.1',  help='Gateway IP to ping (default: 192.168.1.1)')
    parser.add_argument('--internet', default='8.8.8.8',      help='Internet host to ping (default: 8.8.8.8)')
    parser.add_argument('--output',   default=DEFAULT_OUTPUT,  help='Output JSON path')
    parser.add_argument('--history',  default=DEFAULT_HISTORY, help='History JSON path')
    parser.add_argument('--max-history', type=int, default=MAX_HISTORY, help='Max history entries (default: 48)')
    args = parser.parse_args()

    now = datetime.now().isoformat()
    print(f"[{datetime.now():%H:%M:%S}] Running network diagnostics...")

    print(f"  Pinging gateway ({args.gateway})...")
    gw_latency = ping_latency(args.gateway)
    print(f"    Gateway avg: {gw_latency['avg']}ms")

    print(f"  Pinging internet ({args.internet})...")
    inet_latency = ping_latency(args.internet)
    print(f"    Internet avg: {inet_latency['avg']}ms")

    speed = run_speedtest()
    print(f"  Download: {speed['download_mbps']} Mbps  Upload: {speed['upload_mbps']} Mbps")

    result = {
        "timestamp":        now,
        "gateway_latency":  gw_latency,
        "internet_latency": inet_latency,
        "speed":            speed,
    }

    history = load_history(args.history)
    history.append(result)
    history = history[-args.max_history:]

    with open(args.history, 'w') as f:
        json.dump(history, f, indent=2)

    output = {"latest": result, "history": history, "updated": now}
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"  Saved → {args.output}")


if __name__ == '__main__':
    main()
