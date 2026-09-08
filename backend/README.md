# ConAI Backend

FastAPI backend for the ConAI Dynamic Knowledge Management & Conversational AI Platform.

---

## Prerequisites

- Python 3.11+  
- Node.js 20+ (for the frontend)

---

## Quick Start

### 1 — Clone / extract and navigate into the backend

```bash
cd ConAI-Backend/backend
```

### 2 — Create a virtual environment and install dependencies

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3 — Configure environment variables

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux
```

Edit `.env` if you want to use PostgreSQL or change the JWT secret.  
The default SQLite config works out of the box — no DB setup required.

### 4 — Run the backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server starts at **http://localhost:8000**.  
Interactive API docs: **http://localhost:8000/docs**

### 5 — Seed demo data (first run only)

In a second terminal (with the venv activated):

```bash
python seed.py
```

This creates:

| Role | Email | Password |
|---|---|---|
| Admin | `olivia.bennett@conai.com` | `Admin@1234` |
| Employee | `marcus.chen@conai.com` | `Employee@1234` |
| Employee | `aisha.patel@conai.com` | `Employee@1234` |
| Employee | `daniel.foster@conai.com` | `Employee@1234` |

Plus 4 realistic knowledge sources with pre-indexed chunks so the AI chat demo works immediately.

---

## Running the Frontend

```bash
cd ConAI-Backend/ConAI-front
npm install        # skip if node_modules already present
npm run dev
```

The Vite dev server starts at **http://localhost:5173**.

Set `VITE_API_URL` if your backend runs on a different port:

```bash
# Windows PowerShell
$env:VITE_API_URL="http://localhost:8000"; npm run dev
```

---

## Project Structure

```
backend/
├── app/
│   ├── main.py            ← FastAPI app, CORS, scheduler
│   ├── database.py        ← SQLAlchemy engine + session
│   ├── models.py          ← ORM models
│   ├── schemas.py         ← Pydantic request/response schemas
│   ├── auth.py            ← JWT, bcrypt, RBAC dependencies
│   ├── routers/
│   │   ├── auth.py        ← POST /api/auth/{signup,login,logout,me}
│   │   ├── users.py       ← CRUD /api/users + CSV export
│   │   ├── sources.py     ← CRUD /api/sources + ingestion + sync
│   │   ├── chat.py        ← /api/chat/sessions + messages
│   │   ├── threads.py     ← /api/threads (admin↔employee)
│   │   ├── notifications.py
│   │   └── dashboard.py   ← /api/dashboard/stats
│   └── services/
│       ├── ingestion.py   ← Parser dispatch + chunker
│       └── ai_responder.py ← ⭐ Swap this for the real RAG agent
├── uploads/               ← Uploaded files (local storage)
├── seed.py                ← Demo data seed
├── requirements.txt
├── .env.example
└── README.md
```

---

## Swapping in the Real AI Agent

Edit **`app/services/ai_responder.py`** — replace the body of `respond()`:

```python
def respond(question: str, db: Session) -> tuple[str, list[int]]:
    # Replace this block with your RAG / LLM call
    reply = your_rag_agent.answer(question)
    cited_source_ids = your_rag_agent.cited_sources()
    return reply, cited_source_ids
```

No other file needs to change.

---

## Migrating to PostgreSQL

1. Install PostgreSQL and create a database:
   ```sql
   CREATE DATABASE conai;
   CREATE USER conai WITH PASSWORD 'password';
   GRANT ALL ON DATABASE conai TO conai;
   ```

2. Update `.env`:
   ```
   DATABASE_URL=postgresql://conai:password@localhost:5432/conai
   ```

3. Re-run the server — SQLAlchemy will create tables on startup.

---

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/signup` | public | Register |
| POST | `/api/auth/login` | public | Login, returns JWT |
| GET | `/api/auth/me` | bearer | Current user |
| GET | `/api/users` | bearer | List users |
| POST | `/api/users` | admin | Create user |
| GET | `/api/users/export` | admin | CSV download |
| PATCH | `/api/users/{id}` | admin | Update user |
| DELETE | `/api/users/{id}` | admin | Delete user |
| GET | `/api/sources` | bearer | List knowledge sources |
| POST | `/api/sources` | admin | Upload file or add URL |
| GET | `/api/sources/{id}` | bearer | Get source |
| PATCH | `/api/sources/{id}` | admin | Update / re-index |
| DELETE | `/api/sources/{id}` | admin | Delete source |
| GET | `/api/sources/{id}/status` | bearer | Ingestion status |
| POST | `/api/sources/{id}/resync` | admin | Trigger re-index |
| GET | `/api/sources/{id}/file` | bearer | Download file |
| GET | `/api/sources/{id}/versions` | bearer | Version history |
| POST | `/api/sources/{id}/sync-policy` | admin | Set cron schedule |
| GET | `/api/chat/sessions` | bearer | List AI sessions |
| POST | `/api/chat/sessions` | bearer | New session |
| POST | `/api/chat/sessions/{id}/messages` | bearer | Send message |
| GET | `/api/threads` | bearer | List threads |
| POST | `/api/threads` | bearer | Create thread |
| POST | `/api/threads/{id}/messages` | bearer | Post message |
| GET | `/api/notifications` | bearer | Unread notifications |
| POST | `/api/notifications/{id}/read` | bearer | Mark read |
| GET | `/api/dashboard/stats` | bearer | Dashboard counts |
| GET | `/health` | public | Health check |
