"""
Static Pages and Template Routes
Serves HTML pages and static file references
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from ..core.config import get_settings
from ..core.logging import setup_logging

router = APIRouter(tags=["static"])
logger = setup_logging(__name__)
settings = get_settings()

# Setup templates
templates = Jinja2Templates(directory=settings.TEMPLATE_DIR)
templates.env.auto_reload = settings.DEBUG
templates.env.cache = None if settings.DEBUG else {}


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root(request: Request):
    """Serve main application page"""
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(request: Request):
    """Serve dashboard page"""
    return templates.TemplateResponse("curriculum_dashboard.html", {"request": request})


@router.get("/innerverse", response_class=HTMLResponse, include_in_schema=False)
async def innerverse_page(request: Request):
    """Serve InnerVerse main interface"""
    try:
        return templates.TemplateResponse("innerverse.html", {"request": request})
    except Exception as e:
        logger.error(f"Error serving innerverse page: {e}")
        return templates.TemplateResponse("index.html", {"request": request})


@router.get("/uploader", response_class=HTMLResponse, include_in_schema=False)
async def uploader_page(request: Request):
    """Serve document uploader page"""
    return FileResponse("uploader-full.html")


@router.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
async def privacy_page():
    """Serve privacy policy page"""
    return FileResponse("privacy.html")


@router.get("/migration", response_class=HTMLResponse, include_in_schema=False)
async def migration_page():
    """Serve migration utility page"""
    return FileResponse("migration.html")


@router.get("/content-atlas", response_class=HTMLResponse, include_in_schema=False)
async def content_atlas_page():
    """Serve content atlas page"""
    return FileResponse("content-atlas.html")


@router.get("/knowledge-graph", response_class=HTMLResponse, include_in_schema=False)
async def knowledge_graph_page():
    """Serve knowledge graph visualization page"""
    return FileResponse("knowledge-graph.html")


@router.get("/learning-paths", response_class=HTMLResponse, include_in_schema=False)
async def learning_paths_page(request: Request):
    """Serve learning paths interface"""
    return templates.TemplateResponse("learning_paths.OLD.html", {"request": request})


# Icon routes
@router.get("/brain-icon-192.png", include_in_schema=False)
async def brain_icon_192():
    """Serve brain icon 192x192"""
    return FileResponse("icons/icon-192x192.png")


@router.get("/brain-icon-512.png", include_in_schema=False)
async def brain_icon_512():
    """Serve brain icon 512x512"""
    return FileResponse("icons/icon-512x512.png")


# Claude app versions (legacy)
claude_versions = list(range(12, 27))  # v12 through v26

for version in claude_versions:
    @router.get(f"/claude-app.v{version}.js", include_in_schema=False)
    async def claude_app_version():
        """Serve Claude app JavaScript (version)"""
        return FileResponse("claude-app.js")

@router.get("/claude-app.js", include_in_schema=False)
async def claude_app_js():
    """Serve Claude app JavaScript"""
    return FileResponse("claude-app.js")

