"""Seed script — populates demo users and sample knowledge sources.

Run once after the app has started (tables must exist):
    python seed.py

Creates:
  - 1 ADMIN: Olivia Bennett  (olivia.bennett@conai.com / Admin@1234)
  - 1 EMPLOYEE: Marcus Chen  (marcus.chen@conai.com / Employee@1234)
  - 4 knowledge sources (mix of types) with realistic metadata
  - Welcome message thread for Marcus
"""
import datetime
import os
import sys

# Ensure we can import from the app package
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal, engine
from app.models import Base, ChatMessage, ChatSession, KnowledgeChunk, KnowledgeSource, MessageThread, ThreadMessage, User
from app.auth import hash_password

ADMIN_PASSWORD = "Admin@1234"
EMPLOYEE_PASSWORD = "Employee@1234"


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ── Skip if already seeded ─────────────────────────────────────────
        if db.query(User).count() > 0:
            print("Database already seeded. Skipping.")
            return

        # ── Users ──────────────────────────────────────────────────────────
        admin = User(
            name="Olivia Bennett",
            initials="OB",
            employee_id="EMP-1048",
            email="olivia.bennett@conai.com",
            hashed_password=hash_password(ADMIN_PASSWORD),
            role="ADMIN",
            department="Operations",
            salary="$128,400",
            status="Active",
            joined="Jan 08, 2023",
            color="rose",
        )
        marcus = User(
            name="Marcus Chen",
            initials="MC",
            employee_id="EMP-1092",
            email="marcus.chen@conai.com",
            hashed_password=hash_password(EMPLOYEE_PASSWORD),
            role="EMPLOYEE",
            department="Engineering",
            salary="$112,600",
            status="Active",
            joined="Feb 14, 2023",
            color="blue",
        )
        aisha = User(
            name="Aisha Patel",
            initials="AP",
            employee_id="EMP-1107",
            email="aisha.patel@conai.com",
            hashed_password=hash_password(EMPLOYEE_PASSWORD),
            role="EMPLOYEE",
            department="People & Culture",
            salary="$96,800",
            status="Active",
            joined="Mar 22, 2023",
            color="violet",
        )
        daniel = User(
            name="Daniel Foster",
            initials="DF",
            employee_id="EMP-1154",
            email="daniel.foster@conai.com",
            hashed_password=hash_password(EMPLOYEE_PASSWORD),
            role="EMPLOYEE",
            department="Finance",
            salary="$104,200",
            status="Active",
            joined="Apr 03, 2023",
            color="amber",
        )

        for u in [admin, marcus, aisha, daniel]:
            db.add(u)
        db.flush()

        print(f"  [OK] Created {db.query(User).count()} users")

        # ── Knowledge sources ──────────────────────────────────────────────
        sources_data = [
            {
                "name": "Information Security Policy",
                "description": "Guidelines for protecting company systems, data, and customer information.",
                "source_type": "pdf",
                "status": "published",
                "version": 2,
                "uploader": admin,
                "size_bytes": 2_400_000,
            },
            {
                "name": "Remote Work & Flexibility",
                "description": "Principles and expectations for working effectively from anywhere.",
                "source_type": "docx",
                "status": "published",
                "version": 1,
                "uploader": admin,
                "size_bytes": 1_800_000,
            },
            {
                "name": "Employee Code of Conduct",
                "description": "Shared standards for a respectful, inclusive, and ethical workplace.",
                "source_type": "pdf",
                "status": "published",
                "version": 3,
                "uploader": aisha,
                "size_bytes": 3_100_000,
            },
            {
                "name": "Expense & Travel Policy",
                "description": "Clear guide to business travel, expenses, and reimbursement.",
                "source_type": "xlsx",
                "status": "draft",
                "version": 1,
                "uploader": daniel,
                "size_bytes": 1_200_000,
            },
        ]

        chunk_texts = {
            "Information Security Policy": [
                "All employees must use multi-factor authentication (MFA) on all company accounts. "
                "MFA significantly reduces unauthorized access risk. Failure to comply may result in "
                "suspension of access privileges.",
                "Data classification levels: Public, Internal, Confidential, and Restricted. "
                "Restricted data includes personal employee information, financial records, "
                "and strategic plans. Restricted data must be encrypted at rest and in transit.",
                "Incident reporting: Any suspected security incident must be reported to the "
                "IT Security team within 1 hour of discovery. Use the #security-incidents Slack channel "
                "or email security@conai.com. Do not attempt to contain the incident yourself.",
            ],
            "Remote Work & Flexibility": [
                "Employees may work remotely up to 3 days per week. Team leads must be notified "
                "at least 24 hours in advance for remote days. Core hours of 10 AM – 3 PM local "
                "time must be observed for meetings and collaboration.",
                "Home office equipment: ConAI provides a laptop and monitor allowance of $500 per "
                "year for remote setup. Receipts must be submitted within 30 days. A standing desk "
                "allowance of $300 is available once every 3 years.",
            ],
            "Employee Code of Conduct": [
                "ConAI is committed to maintaining a workplace free from discrimination and harassment. "
                "All employees must treat colleagues with dignity and respect. "
                "Any form of harassment based on race, gender, religion, age, or disability is strictly prohibited.",
                "Conflicts of interest must be disclosed to HR immediately. "
                "This includes relationships with vendors, clients, or competitors. "
                "Outside employment must be pre-approved by your manager.",
            ],
            "Expense & Travel Policy": [
                "Economy class airfare is required for flights under 4 hours. "
                "Business class may be approved by VP-level and above for flights over 6 hours. "
                "All flights must be booked through the company travel portal.",
                "Per diem rates: Meals $75/day (domestic), $100/day (international). "
                "Hotel stays must not exceed $200/night without manager approval. "
                "Receipts over $25 must be submitted for reimbursement.",
            ],
        }

        for s_data in sources_data:
            source = KnowledgeSource(
                name=s_data["name"],
                description=s_data["description"],
                source_type=s_data["source_type"],
                status=s_data["status"],
                ingestion_status="indexed",
                version=s_data["version"],
                uploaded_by_id=s_data["uploader"].id,
                size_bytes=s_data["size_bytes"],
            )
            db.add(source)
            db.flush()

            # Add pre-built chunks for demo searchability
            for idx, text in enumerate(chunk_texts.get(s_data["name"], [])):
                chunk = KnowledgeChunk(
                    source_id=source.id,
                    chunk_index=idx,
                    text=text,
                    metadata_json='{"seeded": true}',
                )
                db.add(chunk)

        print(f"  [OK] Created {len(sources_data)} knowledge sources with demo chunks")

        # ── Message threads ────────────────────────────────────────────────
        for emp in [marcus, aisha, daniel]:
            thread = MessageThread(employee_id=emp.id)
            db.add(thread)
            db.flush()
            welcome = ThreadMessage(
                thread_id=thread.id,
                from_="assistant",
                text=f"Hi {emp.name.split()[0]}, how can I help with a company policy today?",
                sender_name="ConAI Assistant",
            )
            db.add(welcome)

        print("  [OK] Created message threads for employees")

        # ── AI chat sessions for admin ─────────────────────────────────────
        session_seeds = [
            ("Leave Policy", "Hi, I am ConAI AI. Ask me anything about the policies and knowledge uploaded to your workspace."),
            ("Employee Benefits", "I can help explain employee benefits and workplace programs."),
            ("IT Security", "Ask me about information security policies and good security practices."),
            ("Work From Home", "Ask me about remote work and flexibility guidelines."),
        ]
        for title, greeting in session_seeds:
            session = ChatSession(title=title, user_id=admin.id)
            db.add(session)
            db.flush()
            msg = ChatMessage(session_id=session.id, from_="assistant", text=greeting, source_ids="[]")
            db.add(msg)

        print("  [OK] Created seed AI chat sessions")

        db.commit()
        print("\n[DONE] Seed complete!")
        print(f"   Admin login:    olivia.bennett@conai.com  /  {ADMIN_PASSWORD}")
        print(f"   Employee login: marcus.chen@conai.com     /  {EMPLOYEE_PASSWORD}")

    except Exception as exc:
        db.rollback()
        print(f"Seed failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
