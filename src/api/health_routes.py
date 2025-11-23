"""
Health Check and Status Routes
"""
from fastapi import APIRouter, Response
from ..core.config import get_settings
from ..core.database import get_db_connection
from ..core.logging import setup_logging

router = APIRouter(tags=["health"])
logger = setup_logging(__name__)
settings = get_settings()


@router.get("/health", include_in_schema=False)
async def health_check():
    """
    Health check endpoint for monitoring
    Returns application status and configuration validation
    """
    validation = settings.validate_required_keys()
    
    # Check database connection
    db_status = "connected"
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except Exception as e:
        db_status = f"error: {str(e)}"
        logger.error(f"Database health check failed: {e}")
    
    return {
        "status": "healthy" if validation["valid"] and db_status == "connected" else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "config_validation": {
            "required_keys_present": validation["valid"],
            "missing_required": validation["missing_required"],
            "missing_optional": validation["missing_optional"],
        }
    }


@router.get("/api/usage")
async def get_api_usage():
    """Get API usage statistics from database"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Total cost
                cursor.execute("SELECT COALESCE(SUM(cost), 0) as total FROM api_usage")
                total_cost = cursor.fetchone()['total']
                
                # Cost by operation
                cursor.execute("""
                    SELECT operation, COALESCE(SUM(cost), 0) as total
                    FROM api_usage
                    GROUP BY operation
                    ORDER BY total DESC
                """)
                by_operation = [dict(row) for row in cursor.fetchall()]
                
                # Recent usage
                cursor.execute("""
                    SELECT timestamp, operation, model, input_tokens, output_tokens, cost
                    FROM api_usage
                    ORDER BY timestamp DESC
                    LIMIT 100
                """)
                recent = [dict(row) for row in cursor.fetchall()]
                
                return {
                    "total_cost": float(total_cost),
                    "by_operation": by_operation,
                    "recent": recent
                }
    except Exception as e:
        logger.error(f"Error fetching API usage: {e}", exc_info=True)
        return {
            "error": "Failed to fetch usage statistics",
            "detail": str(e)
        }

