import re
import subprocess
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from app.auth import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/security", dependencies=[Depends(require_auth)])

IP_RE = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3})")


def parse_auth_log(days: int = 7):
    """Read SSH failures from journald (Debian 13 uses journald, no auth.log)."""
    failed = []
    cutoff = datetime.now() - timedelta(days=days)
    since = cutoff.strftime("%Y-%m-%d %H:%M:%S")

    try:
        result = subprocess.run(
            ["journalctl", "_SYSTEMD_UNIT=sshd.service", "--since", since,
             "--no-pager", "-o", "short-iso"],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.splitlines():
            if "Failed password" not in line and "Invalid user" not in line:
                continue
            # ISO timestamp: 2026-03-22T10:00:00+0200
            ts_m = re.match(r"^(\d{4}-\d{2}-\d{2}T[\d:]+)", line)
            try:
                dt = datetime.fromisoformat(ts_m.group(1)) if ts_m else datetime.now()
            except ValueError:
                dt = datetime.now()
            ip_m = IP_RE.search(line)
            failed.append({
                "timestamp": dt.isoformat(),
                "ip": ip_m.group(1) if ip_m else "unknown",
                "line": line.strip(),
            })
    except Exception:
        pass

    return failed


def get_fail2ban_status():
    try:
        result = subprocess.run(
            ["fail2ban-client", "status", "sshd"],
            capture_output=True, text=True, timeout=5
        )
        banned_ips = []
        for line in result.stdout.splitlines():
            if "Banned IP list" in line:
                ips = line.split(":")[-1].strip()
                banned_ips = [ip.strip() for ip in ips.split() if ip.strip()]
        total_banned = 0
        for line in result.stdout.splitlines():
            if "Total banned" in line:
                try:
                    total_banned = int(line.split(":")[-1].strip())
                except ValueError:
                    pass
        return {"active_bans": banned_ips, "total_banned": total_banned, "available": True}
    except Exception:
        return {"active_bans": [], "total_banned": 0, "available": False}


@router.get("/summary")
async def security_summary(days: int = Query(default=7, le=30)):
    failed = parse_auth_log(days)
    ip_counts = {}
    for e in failed:
        ip_counts[e["ip"]] = ip_counts.get(e["ip"], 0) + 1
    top_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    f2b = get_fail2ban_status()
    return {
        "total_failed_attempts": len(failed),
        "unique_ips": len(ip_counts),
        "top_attacking_ips": [{"ip": ip, "count": c} for ip, c in top_ips],
        "fail2ban": f2b,
        "recent_events": failed[-50:],
    }


@router.get("/events")
async def security_events(
    limit: int = Query(default=100, le=500),
    db=Depends(get_db),
):
    async with db.execute(
        "SELECT * FROM security_events ORDER BY timestamp DESC LIMIT ?", (limit,)
    ) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]
