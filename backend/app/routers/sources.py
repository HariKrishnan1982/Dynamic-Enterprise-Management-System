"""Knowledge sources (policies) router.

File upload goes to local /uploads/ directory; source_url for websites/databases.
Background ingestion starts immediately on upload or resync.
"""
import hashlib
import json
import os
import threading
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth import AdminUser, CurrentUser
from app.database import SessionLocal, get_db
from app.models import KnowledgeSource, KnowledgeSourceVersion, SyncPolicy
from app.schemas import (
    SourceCreate,
    SourceOut,
    SourceStatusOut,
    SourceUpdate,
    SourceVersionOut,
    SyncPolicyCreate,
    SyncPolicyOut,
)
from app.services.ingestion import ingest_source

router = APIRouter(prefix="/api/sources", tags=["sources"])

UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", "uploads")).resolve()
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / 1024 / 1024:.1f} MB"


def _format_date(dt) -> str:
    if not dt:
        return "—"
    return dt.strftime("%b %d, %Y")


def _to_out(source: KnowledgeSource) -> SourceOut:
    uploader_name = source.uploader.name if source.uploader else "Unknown"
    file_url = f"/api/sources/{source.id}/file" if source.file_path else None
    # Capitalise status to match frontend: "Draft" | "Published"
    status_display = source.status.capitalize() if source.status else "Draft"
    return SourceOut(
        id=source.id,
        name=source.name,
        description=source.description,
        date=_format_date(source.created_at),
        uploadedBy=uploader_name,
        version=f"v{source.version}.0",
        status=status_display,
        size=_format_size(source.size_bytes),
        file=file_url,
        sourceType=source.source_type,
        ingestionStatus=source.ingestion_status,
    )


def _db_factory():
    return SessionLocal()


def _kick_ingestion(source_id: int):
    """Start ingestion in a daemon thread so the HTTP response returns quickly."""
    t = threading.Thread(target=ingest_source, args=(source_id, _db_factory), daemon=True)
    t.start()


# ─── List ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[SourceOut])
def list_sources(
    current_user: CurrentUser,
    status: str | None = None,
    source_type: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(KnowledgeSource)
    if status:
        q = q.filter(KnowledgeSource.status == status.lower())
    if source_type:
        q = q.filter(KnowledgeSource.source_type == source_type.lower())
    sources = q.order_by(KnowledgeSource.created_at.desc()).all()
    return [_to_out(s) for s in sources]


# ─── Create (multipart for files OR JSON body for URLs) ──────────────────────

@router.post("", response_model=SourceOut)
async def create_source(
    admin: AdminUser,
    db: Session = Depends(get_db),
    # Form fields (for file uploads)
    name: str = Form(None),
    description: str = Form(""),
    source_type: str = Form("pdf"),
    source_url: str = Form(None),
    status: str = Form("draft"),
    file: UploadFile = File(None),
):
    if not name:
        raise HTTPException(status_code=400, detail="name is required.")

    file_path_str: str | None = None
    size_bytes = 0
    checksum: str | None = None

    if file and file.filename:
        contents = await file.read()
        size_bytes = len(contents)
        checksum = hashlib.sha256(contents).hexdigest()
        # Detect type from extension if not explicitly set
        ext = Path(file.filename).suffix.lower().lstrip(".")
        if ext in ("pdf", "docx", "xlsx", "txt"):
            source_type = ext
        save_path = UPLOADS_DIR / f"{checksum[:16]}_{file.filename}"
        save_path.write_bytes(contents)
        file_path_str = str(save_path)

    source = KnowledgeSource(
        name=name,
        description=description,
        source_type=source_type,
        status=status,
        uploaded_by_id=admin.id,
        file_path=file_path_str,
        source_url=source_url,
        size_bytes=size_bytes,
        checksum=checksum,
        ingestion_status="pending",
        version=1,
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    # Version snapshot
    ver = KnowledgeSourceVersion(
        source_id=source.id,
        version=1,
        file_path=file_path_str,
        created_by_id=admin.id,
    )
    db.add(ver)
    db.commit()

    # Kick background ingestion
    _kick_ingestion(source.id)

    return _to_out(source)


# ─── Get single ───────────────────────────────────────────────────────────────

@router.get("/{source_id}", response_model=SourceOut)
def get_source(source_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    source = db.get(KnowledgeSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")
    return _to_out(source)


# ─── Update ───────────────────────────────────────────────────────────────────

@router.patch("/{source_id}", response_model=SourceOut)
async def update_source(
    source_id: int,
    admin: AdminUser,
    db: Session = Depends(get_db),
    name: str = Form(None),
    description: str = Form(None),
    status: str = Form(None),
    source_url: str = Form(None),
    file: UploadFile = File(None),
):
    source = db.get(KnowledgeSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")

    if name:
        source.name = name
    if description is not None:
        source.description = description
    if status:
        source.status = status.lower()
    if source_url:
        source.source_url = source_url
        source.ingestion_status = "pending"

    if file and file.filename:
        contents = await file.read()
        checksum = hashlib.sha256(contents).hexdigest()
        ext = Path(file.filename).suffix.lower().lstrip(".")
        save_path = UPLOADS_DIR / f"{checksum[:16]}_{file.filename}"
        save_path.write_bytes(contents)
        source.file_path = str(save_path)
        source.size_bytes = len(contents)
        source.checksum = checksum
        if ext in ("pdf", "docx", "xlsx", "txt"):
            source.source_type = ext
        source.ingestion_status = "pending"

    source.version += 1

    # Version snapshot
    ver = KnowledgeSourceVersion(
        source_id=source.id,
        version=source.version,
        file_path=source.file_path,
        created_by_id=admin.id,
    )
    db.add(ver)
    db.commit()
    db.refresh(source)

    if source.ingestion_status == "pending":
        _kick_ingestion(source.id)

    return _to_out(source)


# ─── Delete ───────────────────────────────────────────────────────────────────

@router.delete("/{source_id}")
def delete_source(source_id: int, admin: AdminUser, db: Session = Depends(get_db)):
    source = db.get(KnowledgeSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")
    db.delete(source)
    db.commit()
    return {"detail": "Source deleted."}


# ─── Versions ─────────────────────────────────────────────────────────────────

@router.get("/{source_id}/versions", response_model=list[SourceVersionOut])
def list_versions(source_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    source = db.get(KnowledgeSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")
    return source.versions


# ─── Ingestion status ─────────────────────────────────────────────────────────

@router.get("/{source_id}/status", response_model=SourceStatusOut)
def ingestion_status(source_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    source = db.get(KnowledgeSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")
    return SourceStatusOut(
        id=source.id,
        ingestionStatus=source.ingestion_status,
        ingestionError=source.ingestion_error,
    )


# ─── Resync ───────────────────────────────────────────────────────────────────

@router.post("/{source_id}/resync")
def resync_source(source_id: int, admin: AdminUser, db: Session = Depends(get_db)):
    source = db.get(KnowledgeSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")
    source.ingestion_status = "pending"
    db.commit()
    _kick_ingestion(source.id)
    return {"detail": "Resync started.", "source_id": source_id}


# ─── File download ────────────────────────────────────────────────────────────

@router.get("/{source_id}/file")
def download_file(source_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    source = db.get(KnowledgeSource, source_id)
    if not source or not source.file_path:
        raise HTTPException(status_code=404, detail="File not found.")
    file_path = Path(source.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing from storage.")
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )


# ─── Sync policy ─────────────────────────────────────────────────────────────

@router.post("/{source_id}/sync-policy", response_model=SyncPolicyOut)
def set_sync_policy(
    source_id: int,
    body: SyncPolicyCreate,
    admin: AdminUser,
    db: Session = Depends(get_db),
):
    source = db.get(KnowledgeSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")

    existing = db.query(SyncPolicy).filter(SyncPolicy.source_id == source_id).first()
    if existing:
        existing.schedule = body.schedule
        existing.enabled = body.enabled
        policy = existing
    else:
        policy = SyncPolicy(source_id=source_id, schedule=body.schedule, enabled=body.enabled)
        db.add(policy)
    db.commit()
    db.refresh(policy)

    # Register with APScheduler (imported lazily to avoid circular)
    try:
        from app.main import scheduler  # type: ignore
        job_id = f"sync_{source_id}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
        if body.enabled:
            scheduler.add_job(
                _kick_ingestion,
                "cron",
                args=[source_id],
                id=job_id,
                **_parse_cron(body.schedule),
            )
    except Exception:
        pass  # scheduler not yet started during tests

    return policy


def _parse_cron(cron_str: str) -> dict:
    """Convert '*/5 * * * *' to APScheduler kwargs."""
    parts = cron_str.strip().split()
    if len(parts) != 5:
        return {"minute": "*/30"}
    keys = ["minute", "hour", "day", "month", "day_of_week"]
    return {k: v for k, v in zip(keys, parts)}
