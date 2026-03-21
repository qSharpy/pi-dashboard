import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

from app.database import init_db
from app.auth import verify_password, create_token, require_auth
from app.routes import metrics, security, reports, events


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)

app.include_router(metrics.router)
app.include_router(security.router)
app.include_router(reports.router)
app.include_router(events.router)


class LoginRequest(BaseModel):
    password: str


@app.post("/auth/login")
async def login(req: LoginRequest, response: Response):
    if not verify_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid password")
    token = create_token()
    response.set_cookie(
        "session", token,
        httponly=True, secure=True, samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return {"ok": True}


@app.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("session")
    return {"ok": True}


@app.get("/auth/check")
async def auth_check(_=Depends(require_auth)):
    return {"ok": True}


# Serve static frontend
FRONTEND = "/frontend"
app.mount("/assets", StaticFiles(directory=f"{FRONTEND}/assets"), name="assets")


@app.get("/login")
async def login_page():
    return FileResponse(f"{FRONTEND}/login.html")


@app.get("/")
async def root():
    return RedirectResponse("/dashboard")


@app.get("/{page}")
async def spa(page: str):
    path = f"{FRONTEND}/{page}.html"
    if os.path.exists(path):
        return FileResponse(path)
    return FileResponse(f"{FRONTEND}/dashboard.html")
