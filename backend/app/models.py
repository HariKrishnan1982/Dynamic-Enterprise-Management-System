"""SQLAlchemy ORM models for ConAI.

Data shapes are aligned with the frontend's expected JSON:
  User        → name, initials, employeeId, email, role, department, salary,
                status, joined, color, permissions
  KnowledgeSource (Policy) → id, name, description, date, uploadedBy, version,
                              status, size, file
  ChatSession / ChatMessage → id, title, messages
  MessageThread / ThreadMessage → id, employeeId, employeeName, messages
  Notification → id, text
"""
import datetime
import json
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ─── User ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    initials: Mapped[str] = mapped_column(String(4), nullable=False)
    employee_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="EMPLOYEE")
    department: Mapped[str] = mapped_column(String(100), nullable=False, default="General")
    salary: Mapped[str] = mapped_column(String(30), nullable=False, default="Pending")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Active")
    joined: Mapped[str] = mapped_column(String(30), nullable=False)
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="blue")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # relationships
    sources: Mapped[list["KnowledgeSource"]] = relationship(
        "KnowledgeSource", back_populates="uploader", foreign_keys="KnowledgeSource.uploaded_by_id"
    )
    chat_sessions: Mapped[list["ChatSession"]] = relationship("ChatSession", back_populates="user")
    thread: Mapped["MessageThread"] = relationship(
        "MessageThread", back_populates="employee", uselist=False,
        foreign_keys="MessageThread.employee_id"
    )
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="user")


# ─── Knowledge Source (Policy) ───────────────────────────────────────────────

class KnowledgeSource(Base):
    """Unified knowledge source — policies are source_type='pdf'/'docx'/etc."""
    __tablename__ = "knowledge_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pdf"
    )  # pdf|docx|xlsx|txt|url|database|other
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )  # draft|published|archived
    ingestion_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending|processing|indexed|failed
    ingestion_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    uploaded_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    uploader: Mapped["User | None"] = relationship(
        "User", back_populates="sources", foreign_keys=[uploaded_by_id]
    )
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        "KnowledgeChunk", back_populates="source", cascade="all, delete-orphan"
    )
    versions: Mapped[list["KnowledgeSourceVersion"]] = relationship(
        "KnowledgeSourceVersion", back_populates="source", cascade="all, delete-orphan"
    )
    sync_policy: Mapped["SyncPolicy | None"] = relationship(
        "SyncPolicy", back_populates="source", uselist=False, cascade="all, delete-orphan"
    )


class KnowledgeSourceVersion(Base):
    __tablename__ = "knowledge_source_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("knowledge_sources.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_by_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    source: Mapped["KnowledgeSource"] = relationship("KnowledgeSource", back_populates="versions")


class KnowledgeChunk(Base):
    """Retrieval-ready chunks — the AI agent queries this table."""
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("knowledge_sources.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    source: Mapped["KnowledgeSource"] = relationship("KnowledgeSource", back_populates="chunks")

    def get_metadata(self) -> dict:
        return json.loads(self.metadata_json)


class SyncPolicy(Base):
    __tablename__ = "sync_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("knowledge_sources.id"), unique=True, nullable=False
    )
    schedule: Mapped[str] = mapped_column(String(100), nullable=False)  # cron string
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_status: Mapped[str | None] = mapped_column(String(20), nullable=True)

    source: Mapped["KnowledgeSource"] = relationship("KnowledgeSource", back_populates="sync_policy")


# ─── AI Chat ─────────────────────────────────────────────────────────────────

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New conversation")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="chat_sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan",
        order_by="ChatMessage.id"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    from_: Mapped[str] = mapped_column("from_role", String(20), nullable=False)  # user|assistant
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list of source IDs
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")


# ─── Admin ↔ Employee Threads ─────────────────────────────────────────────────

class MessageThread(Base):
    __tablename__ = "message_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    employee: Mapped["User"] = relationship(
        "User", back_populates="thread", foreign_keys=[employee_id]
    )
    messages: Mapped[list["ThreadMessage"]] = relationship(
        "ThreadMessage", back_populates="thread", cascade="all, delete-orphan",
        order_by="ThreadMessage.id"
    )


class ThreadMessage(Base):
    __tablename__ = "thread_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    thread_id: Mapped[int] = mapped_column(Integer, ForeignKey("message_threads.id"), nullable=False)
    from_: Mapped[str] = mapped_column("from_role", String(20), nullable=False)  # admin|employee|assistant
    text: Mapped[str] = mapped_column(Text, nullable=False)
    sender_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    thread: Mapped["MessageThread"] = relationship("MessageThread", back_populates="messages")


# ─── Notifications ────────────────────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="notifications")
