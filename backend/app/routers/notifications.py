"""Notifications router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.database import get_db
from app.models import Notification
from app.schemas import NotificationOut

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(current_user: CurrentUser, db: Session = Depends(get_db)):
    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.read == False)  # noqa: E712
        .order_by(Notification.created_at.desc())
        .all()
    )
    return notifs


@router.post("/{notif_id}/read")
def mark_read(notif_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    notif = db.get(Notification, notif_id)
    if not notif or notif.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found.")
    notif.read = True
    db.commit()
    return {"detail": "Marked as read."}
