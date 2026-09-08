"""Pydantic schemas for request/response serialization.

All response schemas match the exact field names expected by main.jsx.
"""
import datetime
from typing import Any
from pydantic import BaseModel, EmailStr, Field


# ─── Auth ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    identifier: str  # email OR employeeId
    password: str


class SignupRequest(BaseModel):
    name: str
    identifier: str  # email
    employeeId: str
    password: str
    department: str | None = "General"
    role: str = "EMPLOYEE"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── User ────────────────────────────────────────────────────────────────────

class UserPermissions(BaseModel):
    canManageUsers: bool
    canManagePolicies: bool


class UserOut(BaseModel):
    """Matches the shape main.jsx expects for currentUser and the users list."""
    id: int
    name: str
    initials: str
    employeeId: str
    email: str
    role: str
    department: str
    salary: str
    status: str
    joined: str
    color: str
    permissions: UserPermissions

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    name: str
    email: str
    employeeId: str
    password: str
    role: str = "EMPLOYEE"
    department: str = "General"
    salary: str = "Pending"
    color: str = "blue"


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    department: str | None = None
    salary: str | None = None
    role: str | None = None
    status: str | None = None
    color: str | None = None


# ─── Knowledge Source / Policy ───────────────────────────────────────────────

class SourceOut(BaseModel):
    """Matches the policy shape expected by main.jsx (date, uploadedBy, version, size, file)."""
    id: int
    name: str
    description: str
    date: str          # formatted string e.g. "Aug 26, 2024"
    uploadedBy: str
    version: str       # e.g. "v2.4"
    status: str        # "Draft" | "Published"
    size: str          # e.g. "2.4 MB"
    file: str | None   # download URL or None
    sourceType: str
    ingestionStatus: str

    model_config = {"from_attributes": True}


class SourceCreate(BaseModel):
    name: str
    description: str = ""
    source_type: str = "pdf"
    source_url: str | None = None
    status: str = "draft"


class SourceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    source_url: str | None = None


class SourceVersionOut(BaseModel):
    id: int
    source_id: int
    version: int
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class SourceStatusOut(BaseModel):
    id: int
    ingestionStatus: str
    ingestionError: str | None

    model_config = {"from_attributes": True}


class SyncPolicyCreate(BaseModel):
    schedule: str  # cron expression
    enabled: bool = True


class SyncPolicyOut(BaseModel):
    id: int
    source_id: int
    schedule: str
    enabled: bool
    last_run_at: datetime.datetime | None
    last_run_status: str | None

    model_config = {"from_attributes": True}


# ─── AI Chat ─────────────────────────────────────────────────────────────────

class ChatMessageOut(BaseModel):
    id: int
    from_: str = Field(alias="from")
    text: str

    model_config = {"from_attributes": True, "populate_by_name": True}


class ChatSessionOut(BaseModel):
    id: int
    title: str
    messages: list[ChatMessageOut] = []

    model_config = {"from_attributes": True}


class ChatSessionCreate(BaseModel):
    title: str = "New conversation"


class ChatMessageCreate(BaseModel):
    text: str


# ─── Message Threads ─────────────────────────────────────────────────────────

class ThreadMessageOut(BaseModel):
    id: int
    from_: str = Field(alias="from")
    text: str
    senderName: str | None

    model_config = {"from_attributes": True, "populate_by_name": True}


class MessageThreadOut(BaseModel):
    id: int
    employeeId: str
    employeeName: str
    messages: list[ThreadMessageOut] = []

    model_config = {"from_attributes": True}


class ThreadMessageCreate(BaseModel):
    text: str


# ─── Notifications ────────────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id: int
    text: str
    read: bool

    model_config = {"from_attributes": True}


# ─── Dashboard ───────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    totalSources: int
    recentlyUploaded: str       # date string of most recent upload
    recentlyUploadedName: str   # name of most recent source
    ingestionQueueDepth: int
    activeUsers: int
    totalUsers: int
