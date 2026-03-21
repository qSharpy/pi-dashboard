from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/reports", dependencies=[Depends(require_auth)])


class ReportCreate(BaseModel):
    title: str
    content: str


@router.get("/")
async def list_reports(db=Depends(get_db)):
    async with db.execute(
        "SELECT id, timestamp, title FROM reports ORDER BY timestamp DESC"
    ) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


@router.get("/{report_id}")
async def get_report(report_id: int, db=Depends(get_db)):
    async with db.execute(
        "SELECT * FROM reports WHERE id = ?", (report_id,)
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    return dict(row)


@router.post("/")
async def create_report(report: ReportCreate, db=Depends(get_db)):
    async with db.execute(
        "INSERT INTO reports (timestamp, title, content) VALUES (datetime('now'), ?, ?) RETURNING id, timestamp",
        (report.title, report.content),
    ) as cursor:
        row = await cursor.fetchone()
    await db.commit()
    return {"id": row[0], "timestamp": row[1], "title": report.title}
