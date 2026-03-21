import re
import subprocess
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from app.auth import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/security", dependencies=[Depends(require_auth)])

SSH_LOG = "/host_logs/auth.log"
IP_RE = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3})")
DATE_RE = re.compile(r"^(\w{3}\s+\d+\s+[\d:]+)")


def parse_auth_log(days: int = 7):
    failed = []
    cutoff = datetime.now() - timedelta(days=days)
    current_year = datetime.now().year

    try:
        with open(SSH_LOG) as f:
            for line in f:
                if "Failed password" not in line and "Invalid user" not in line:
                    continue
                date_m = DATE_RE.match(line)
                if not date_m:
                    continue
                try:
                    dt = datetime.strptime(
                        f"{current_year} {date_m.group(1)}", "%Y %b %d %H:%M:%S"
                    )
                except ValueError:
                    continue
                if dt < cutoff:
                    continue
                ip_m = IP_RE.search(line)
                failed.append({
                    "timestamp": dt.isoformat(),
                    "ip": ip_m.group(1) if ip_m else "unknown",
                    "line": line.strip(),
                })
    except FileNotFoundError:
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
