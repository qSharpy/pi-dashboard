import aiosqlite
import os

DB_PATH = os.getenv("DB_PATH", "/data/dashboard.db")


async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cpu_percent REAL,
                ram_percent REAL,
                disk_percent REAL,
                temp REAL,
                load_1m REAL,
                load_5m REAL,
                load_15m REAL,
                net_bytes_sent INTEGER,
                net_bytes_recv INTEGER,
                uptime_seconds INTEGER
            );

            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                source_ip TEXT,
                details TEXT
            );

            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS agent_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metrics(timestamp);
            CREATE INDEX IF NOT EXISTS idx_security_ts ON security_events(timestamp);
        """)
        await db.commit()
