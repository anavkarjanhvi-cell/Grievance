"""
FastAPI application entrypoint.

Serves:
  - /api/*         JSON REST API
  - /docs          Swagger UI (auto-generated)
  - /              Frontend (Jinja2 templates + static assets)
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.config import TEMPLATES_DIR, STATIC_DIR, BASE_DIR
from app.models import init_db
from app.routers.api import router as api_router
from app.routers.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="SIH26 — AI Grievance Portal",
    description="AI-based citizen grievance classification, prioritization & duplicate detection",
    version="2.0.0",
    lifespan=lifespan,
)

# Mount static dirs
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/uploads", StaticFiles(directory=str(BASE_DIR / "uploads")), name="uploads")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# API routers
app.include_router(auth_router, prefix="/api")
app.include_router(api_router, prefix="/api")


# --------------------------------------------------------------------------- #
# Frontend page routes
# --------------------------------------------------------------------------- #
@app.get("/", response_class=HTMLResponse, tags=["Pages"])
async def page_citizen(request: Request):
    return templates.TemplateResponse(request, "citizen.html")


@app.get("/login", response_class=HTMLResponse, tags=["Pages"])
async def page_login(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.get("/queue", response_class=HTMLResponse, tags=["Pages"])
async def page_queue(request: Request):
    return templates.TemplateResponse(request, "queue.html")


@app.get("/dashboard", response_class=HTMLResponse, tags=["Pages"])
async def page_dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")


@app.get("/analytics", response_class=HTMLResponse, tags=["Pages"])
async def page_analytics(request: Request):
    return templates.TemplateResponse(request, "analytics.html")


@app.get("/map", response_class=HTMLResponse, tags=["Pages"])
async def page_map(request: Request):
    return templates.TemplateResponse(request, "map.html")


@app.get("/my-complaints", response_class=HTMLResponse, tags=["Pages"])
async def page_my_complaints(request: Request):
    return templates.TemplateResponse(request, "my_complaints.html")
