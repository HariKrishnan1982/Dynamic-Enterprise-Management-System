"""AI chat router — sessions and messages with placeholder responder."""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.database import get_db
from app.models import ChatMessage, ChatSession
from app.schemas import ChatMessageCreate, ChatMessageOut, ChatSessionCreate, ChatSessionOut
from app.services.ai_responder import respond

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _msg_out(msg: ChatMessage) -> ChatMessageOut:
    return ChatMessageOut.model_validate({"id": msg.id, "from": msg.from_, "text": msg.text})


def _session_out(session: ChatSession) -> ChatSessionOut:
    return ChatSessionOut(
        id=session.id,
        title=session.title,
        messages=[_msg_out(m) for m in session.messages],
    )


@router.get("/sessions", response_model=list[ChatSessionOut])
def list_sessions(current_user: CurrentUser, db: Session = Depends(get_db)):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return [_session_out(s) for s in sessions]


@router.post("/sessions", response_model=ChatSessionOut)
def create_session(
    body: ChatSessionCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    session = ChatSession(title=body.title, user_id=current_user.id)
    db.add(session)
    db.flush()
    # Opening assistant message
    greeting = ChatMessage(
        session_id=session.id,
        from_="assistant",
        text=f"Hi {current_user.name.split()[0]}, ask me anything about ConAI knowledge and policies.",
        source_ids="[]",
    )
    db.add(greeting)
    db.commit()
    db.refresh(session)
    return _session_out(session)


@router.get("/sessions/{session_id}", response_model=ChatSessionOut)
def get_session(session_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    session = db.get(ChatSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found.")
    return _session_out(session)


@router.post("/sessions/{session_id}/messages", response_model=ChatSessionOut)
def send_message(
    session_id: int,
    body: ChatMessageCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    session = db.get(ChatSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Store user message
    user_msg = ChatMessage(
        session_id=session_id,
        from_="user",
        text=body.text,
        source_ids="[]",
    )
    db.add(user_msg)

    # Update session title from first user message
    if session.title in ("New conversation", "ConAI AI Chat"):
        session.title = body.text[:28]

    # AI response (placeholder responder)
    reply_text, source_ids = respond(body.text, db)
    ai_msg = ChatMessage(
        session_id=session_id,
        from_="assistant",
        text=reply_text,
        source_ids=json.dumps(source_ids),
    )
    db.add(ai_msg)
    db.commit()
    db.refresh(session)
    return _session_out(session)
