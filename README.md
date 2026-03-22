# pi-dashboard

Self-hosted system dashboard for a Raspberry Pi 5 running Debian 13 (Trixie).
Accessible at [dash.clusterstein.com](https://dash.clusterstein.com) via Cloudflare Tunnel.

## Features

- **Overview** — live CPU, RAM, disk, temp, uptime (auto-refreshes every 5s)
- **Security** — SSH failed attempts, top attacking IPs, fail2ban status
- **History** — charts for CPU / RAM / temp over 24h, 3d, 7d, 30d
- **Reports** — bi-weekly sysadmin reports (Wednesday + Sunday), rendered as markdown
- **Agent Events** — changelog of automated sysadmin actions

## Stack

- **Backend** — FastAPI + SQLite (via aiosqlite)
- **Frontend** — vanilla JS + Chart.js + marked.js
- **Auth** — bcrypt password + JWT cookie (7-day session)
- **Tunnel** — Cloudflare Tunnel (`cloudflared`)
- **Containers** — Docker Compose

## Setup

1. Clone the repo
2. Copy `.env.example` to `secrets.env` and fill in values:
   ```
   PASSWORD_HASH=<bcrypt hash>   # python3 -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"
   JWT_SECRET=<random hex>       # python3 -c "import secrets; print(secrets.token_hex(32))"
   TUNNEL_TOKEN=<cloudflare token>
   ```
   > Dollar signs in `PASSWORD_HASH` must be escaped as `$$` for Docker Compose
3. Start:
   ```bash
   sudo docker compose up -d
   ```

## Metrics collection

System metrics are collected every 15 minutes via cron:
```bash
*/15 * * * * python3 /home/claw/pi-dashboard/scripts/collect_metrics.py
```

## Sysadmin agent

Reports are generated automatically by a Claude Code sysadmin agent running in a persistent tmux session. See `~/.claude/agents/sysadmin.md`.
