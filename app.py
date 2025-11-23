"""
InnerVerse Application Entry Point
Clean, modular FastAPI application setup
"""
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi_csrf_protect.exceptions import CsrfProtectError

# Core imports
from src.core.config import get_settings
from src.core.logging import setup_logging
from src.core.database import init_database_tables, shutdown_database, get_db_manager
from src.core.exceptions import InnerVerseException, http_exception_from_innerverse

# Route imports
from src.api import health_routes, static_routes
from src.routes.chat_routes import router as chat_router
from src.routes.learning_paths_routes import router as learning_paths_router

# Initialize logging and settings
logger = setup_logging("innerverse")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("="*80)
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("="*80)
    
    # Validate configuration
    validation = settings.validate_required_keys()
    if not validation["valid"]:
        logger.error(f"❌ Missing required configuration: {validation['missing_required']}")
        logger.warning("⚠️  Application may not function correctly")
    else:
        logger.info("✅ All required configuration present")
    
    if validation["missing_optional"]:
        logger.warning(f"⚠️  Missing optional configuration: {validation['missing_optional']}")
    
    # Initialize database
    logger.info("📊 Initializing database...")
    try:
        db_manager = get_db_manager()
        db_success = init_database_tables()
        if db_success:
            logger.info("✅ Database initialized successfully")
        else:
            logger.warning("⚠️  Database initialization incomplete")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}", exc_info=True)
        logger.warning("⚠️  Continuing without database - some features may not work")
    
    logger.info("="*80)
    logger.info(f"🌐 Server ready on {settings.HOST}:{settings.PORT}")
    logger.info(f"📖 API docs available at http://{settings.HOST}:{settings.PORT}/docs")
    logger.info(f"🏥 Health check at http://{settings.HOST}:{settings.PORT}/health")
    logger.info("="*80)
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down InnerVerse...")
    shutdown_database()
    logger.info("✅ Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered learning platform for MBTI and personality typology",
    lifespan=lifespan,
    docs_url=None,  # We'll create custom docs endpoint
    redoc_url=None,
)


# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS middleware
cors_origins = settings.get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(InnerVerseException)
async def innerverse_exception_handler(request: Request, exc: InnerVerseException):
    """Handle custom InnerVerse exceptions"""
    logger.error(f"InnerVerse error: {exc.message}", extra={
        "error_code": exc.error_code,
        "details": exc.details,
        "path": request.url.path
    })
    http_exc = http_exception_from_innerverse(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail
    )


@app.exception_handler(CsrfProtectError)
async def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
    """Handle CSRF protection errors"""
    logger.warning(f"CSRF validation failed for {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"error": "CSRF_VALIDATION_FAILED", "message": "CSRF token validation failed"}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True, extra={
        "path": request.url.path,
        "method": request.method
    })
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "detail": str(exc) if settings.DEBUG else None
        }
    )


# ============================================================================
# ROUTES
# ============================================================================

# Custom Swagger UI
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    """Serve custom Swagger UI documentation"""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{settings.APP_NAME} API Documentation"
    )


# Include routers
app.include_router(health_routes.router)
app.include_router(static_routes.router)
app.include_router(chat_router)
app.include_router(learning_paths_router)

# TODO: Add remaining routes from main_legacy.py
# - Document routes (upload, delete, etc.)
# - YouTube routes (transcription, import)
# - Claude conversation routes
# - Knowledge graph routes
# - Course management routes
# - Admin routes


# ============================================================================
# STATIC FILES
# ============================================================================

class NoCacheStaticFiles(StaticFiles):
    """StaticFiles subclass that disables caching for development"""
    
    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        if settings.DEBUG:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


# Mount static directories
app.mount("/static", NoCacheStaticFiles(directory="static"), name="static")

# Mount node_modules if it exists
if Path("node_modules").exists():
    app.mount("/node_modules", StaticFiles(directory="node_modules"), name="node_modules")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )

