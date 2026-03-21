#!/usr/bin/env python3
"""Collect system metrics and store in SQLite. Run every 15 min via cron."""
import os
import sqlite3
import time
import psutil
from datetime import datetime, timezone

DB_PATH = os.getenv("DB_PATH", "/home/claw/pi-dashboard/data/dashboard.db")


def read_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return round(int(f.read()) / 1000, 1)
    except Exception:
        return None


def init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            cpu_percent REAL, ram_percent REAL, disk_percent REAL, temp REAL,
            load_1m REAL, load_5m REAL, load_15m REAL,
            net_bytes_sent INTEGER, net_bytes_recv INTEGER, uptime_seconds INTEGER
        );
        CREATE TABLE IF NOT EXISTS security_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL, event_type TEXT NOT NULL,
            source_ip TEXT, details TEXT
        );
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL, title TEXT NOT NULL, content TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS agent_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL, action TEXT NOT NULL, details TEXT
        );
    """)
    conn.commit()


def collect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()
    load = os.getloadavg()
    uptime = int(time.time() - psutil.boot_time())
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    conn.execute(
        """INSERT INTO metrics
           (timestamp, cpu_percent, ram_percent, disk_percent, temp,
            load_1m, load_5m, load_15m, net_bytes_sent, net_bytes_recv, uptime_seconds)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            ts,
            psutil.cpu_percent(interval=1),
            mem.percent,
            disk.percent,
            read_temp(),
            round(load[0], 2),
            round(load[1], 2),
            round(load[2], 2),
            net.bytes_sent,
            net.bytes_recv,
            uptime,
        ),
    )
    conn.commit()
    conn.close()
    print(f"[{ts}] metrics collected")


if __name__ == "__main__":
    collect()
