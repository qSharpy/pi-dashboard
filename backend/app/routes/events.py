from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.auth import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/events", dependencies=[Depends(require_auth)])


class EventCreate(BaseModel):
    action: str
    details: str | None = None


@router.get("/")
async def list_events(
    limit: int = Query(default=100, le=500),
    db=Depends(get_db),
):
    async with db.execute(
        "SELECT * FROM agent_events ORDER BY timestamp DESC LIMIT ?", (limit,)
    ) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


@router.post("/")
async def create_event(event: EventCreate, db=Depends(get_db)):
    async with db.execute(
        "INSERT INTO agent_events (timestamp, action, details) VALUES (datetime('now'), ?, ?) RETURNING id, timestamp",
        (event.action, event.details),
    ) as cursor:
        row = await cursor.fetchone()
    await db.commit()
    return {"id": row[0], "timestamp": row[1], "action": event.action}
