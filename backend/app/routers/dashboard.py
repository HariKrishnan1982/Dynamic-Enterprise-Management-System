"""Dashboard stats router — real counts from DB."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.database import get_db
from app.models import KnowledgeSource, User
from app.schemas import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(current_user: CurrentUser, db: Session = Depends(get_db)):
    total_sources = db.query(KnowledgeSource).count()
    queue_depth = (
        db.query(KnowledgeSource)
        .filter(KnowledgeSource.ingestion_status.in_(["pending", "processing"]))
        .count()
    )
    active_users = db.query(User).filter(User.status == "Active").count()
    total_users = db.query(User).count()

    # Most recently uploaded source
    latest = (
        db.query(KnowledgeSource)
        .order_by(KnowledgeSource.created_at.desc())
        .first()
    )
    recently_uploaded = latest.created_at.strftime("%b %d") if latest else "—"
    recently_uploaded_name = latest.name if latest else "No uploads yet"

    return DashboardStats(
        totalSources=total_sources,
        recentlyUploaded=recently_uploaded,
        recentlyUploadedName=recently_uploaded_name,
        ingestionQueueDepth=queue_depth,
        activeUsers=active_users,
        totalUsers=total_users,
    )
