"""ConAI FastAPI application entry point."""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

# ─── Scheduler (shared; imported by sources router) ──────────────────────────
scheduler = BackgroundScheduler(timezone="UTC")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create DB tables on startup (Alembic handles migrations in prod)
    from app.database import engine
    from app.models import Base  # noqa: F401 — registers all models
    Base.metadata.create_all(bind=engine)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="ConAI Backend",
    description="Dynamic Knowledge Management & Conversational AI Platform API",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────
from app.routers import auth, chat, dashboard, notifications, sources, threads, users  # noqa: E402

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(sources.router)
app.include_router(chat.router)
app.include_router(threads.router)
app.include_router(notifications.router)
app.include_router(dashboard.router)

# ─── Static uploads ──────────────────────────────────────────────────────────
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", "uploads")).resolve()
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "ConAI Backend"}
