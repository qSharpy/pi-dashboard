import psutil
import time
import os
from fastapi import APIRouter, Depends, Query
from app.auth import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/metrics", dependencies=[Depends(require_auth)])


def read_pi_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return round(int(f.read()) / 1000, 1)
    except Exception:
        return None


@router.get("/live")
async def live_metrics():
    boot_time = psutil.boot_time()
    uptime = int(time.time() - boot_time)
    net = psutil.net_io_counters()
    load = os.getloadavg()
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "ram_percent": mem.percent,
        "ram_used_gb": round(mem.used / 1e9, 2),
        "ram_total_gb": round(mem.total / 1e9, 2),
        "disk_percent": disk.percent,
        "disk_used_gb": round(disk.used / 1e9, 2),
        "disk_total_gb": round(disk.total / 1e9, 2),
        "temp": read_pi_temp(),
        "uptime_seconds": uptime,
        "load_1m": round(load[0], 2),
        "load_5m": round(load[1], 2),
        "load_15m": round(load[2], 2),
        "net_bytes_sent": net.bytes_sent,
        "net_bytes_recv": net.bytes_recv,
    }


@router.get("/history")
async def metric_history(
    hours: int = Query(default=24, le=720),
    db=Depends(get_db),
):
    async with db.execute(
        """SELECT timestamp, cpu_percent, ram_percent, disk_percent, temp,
                  load_1m, net_bytes_sent, net_bytes_recv, uptime_seconds
           FROM metrics
           WHERE timestamp >= datetime('now', ? || ' hours')
           ORDER BY timestamp ASC""",
        (f"-{hours}",),
    ) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]
