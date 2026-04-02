"""Health check router."""
from fastapi import APIRouter
from sqlalchemy.orm import Session
from db.session import get_db
from fastapi import Depends

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Comprehensive health check."""
    # Test database connection
    try:
        db.execute("SELECT 1")
        db_status = "ok"
    except Exception:
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "version": "0.1.0",
    }
