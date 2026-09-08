"""Admin ↔ Employee message threads router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.database import get_db
from app.models import MessageThread, Notification, ThreadMessage, User
from app.schemas import MessageThreadOut, ThreadMessageCreate, ThreadMessageOut

router = APIRouter(prefix="/api/threads", tags=["threads"])


def _tmsg_out(msg: ThreadMessage) -> ThreadMessageOut:
    return ThreadMessageOut.model_validate(
        {"id": msg.id, "from": msg.from_, "text": msg.text, "senderName": msg.sender_name}
    )


def _thread_out(thread: MessageThread) -> MessageThreadOut:
    employee = thread.employee
    return MessageThreadOut(
        id=thread.id,
        employeeId=employee.employee_id,
        employeeName=employee.name,
        messages=[_tmsg_out(m) for m in thread.messages],
    )


@router.get("", response_model=list[MessageThreadOut])
def list_threads(current_user: CurrentUser, db: Session = Depends(get_db)):
    if current_user.role == "ADMIN":
        threads = db.query(MessageThread).all()
    else:
        threads = db.query(MessageThread).filter(
            MessageThread.employee_id == current_user.id
        ).all()
    return [_thread_out(t) for t in threads]


@router.post("", response_model=MessageThreadOut)
def create_thread(current_user: CurrentUser, db: Session = Depends(get_db)):
    """Employee creates a new support thread."""
    existing = db.query(MessageThread).filter(
        MessageThread.employee_id == current_user.id
    ).first()
    if existing:
        return _thread_out(existing)

    thread = MessageThread(employee_id=current_user.id)
    db.add(thread)
    db.flush()
    welcome = ThreadMessage(
        thread_id=thread.id,
        from_="assistant",
        text=f"Hi {current_user.name.split()[0]}, how can I help with a company policy today?",
        sender_name="ConAI Assistant",
    )
    db.add(welcome)
    db.commit()
    db.refresh(thread)
    return _thread_out(thread)


@router.get("/{thread_id}", response_model=MessageThreadOut)
def get_thread(thread_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    thread = db.get(MessageThread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found.")
    if current_user.role != "ADMIN" and thread.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return _thread_out(thread)


@router.post("/{thread_id}/messages", response_model=MessageThreadOut)
def post_message(
    thread_id: int,
    body: ThreadMessageCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    thread = db.get(MessageThread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found.")
    if current_user.role != "ADMIN" and thread.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    from_role = "admin" if current_user.role == "ADMIN" else "employee"
    msg = ThreadMessage(
        thread_id=thread_id,
        from_=from_role,
        text=body.text,
        sender_name=current_user.name,
    )
    db.add(msg)

    # Notify the other party
    if current_user.role == "ADMIN":
        # Notify the employee
        notif = Notification(
            user_id=thread.employee_id,
            text=f"Admin responded to your message.",
        )
    else:
        # Notify all admins
        admins = db.query(User).filter(User.role == "ADMIN").all()
        for admin in admins:
            notif = Notification(
                user_id=admin.id,
                text=f"{current_user.name} sent a new message.",
            )
            db.add(notif)
        notif = None  # already added above

    if notif:
        db.add(notif)
    db.commit()
    db.refresh(thread)
    return _thread_out(thread)
