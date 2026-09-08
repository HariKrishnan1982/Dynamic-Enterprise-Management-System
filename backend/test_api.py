"""Comprehensive automated end-to-end API test suite for ConAI Backend."""
import io
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import User, KnowledgeSource
from seed import run as run_seed

client = TestClient(app)


def test_full_platform_flow():
    # 1. Health check
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # 2. Admin Login
    res = client.post(
        "/api/auth/login",
        json={"identifier": "olivia.bennett@conai.com", "password": "Admin@1234"},
    )
    assert res.status_code == 200, res.text
    admin_data = res.json()
    admin_token = admin_data["access_token"]
    assert admin_data["user"]["role"] == "ADMIN"
    assert admin_data["user"]["permissions"]["canManageUsers"] is True
    assert admin_data["user"]["permissions"]["canManagePolicies"] is True

    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 3. /api/auth/me
    res = client.get("/api/auth/me", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["email"] == "olivia.bennett@conai.com"

    # 4. Employee Login
    res = client.post(
        "/api/auth/login",
        json={"identifier": "marcus.chen@conai.com", "password": "Employee@1234"},
    )
    assert res.status_code == 200
    emp_data = res.json()
    emp_token = emp_data["access_token"]
    assert emp_data["user"]["role"] == "EMPLOYEE"
    assert emp_data["user"]["permissions"]["canManageUsers"] is False
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # 5. RBAC test: Employee cannot create user
    res = client.post(
        "/api/users",
        json={
            "name": "Hacker",
            "email": "hacker@conai.com",
            "employeeId": "EMP-9999",
            "password": "pass",
        },
        headers=emp_headers,
    )
    assert res.status_code == 403

    # 6. Admin creates a user
    res = client.post(
        "/api/users",
        json={
            "name": "Sarah Connor",
            "email": "sarah.connor@conai.com",
            "employeeId": "EMP-2001",
            "password": "Password@123",
            "department": "Security",
            "salary": "$115,000",
            "role": "EMPLOYEE",
        },
        headers=admin_headers,
    )
    assert res.status_code == 200
    sarah = res.json()
    assert sarah["employeeId"] == "EMP-2001"

    # 7. Admin lists users
    res = client.get("/api/users", headers=admin_headers)
    assert res.status_code == 200
    users = res.json()
    assert len(users) >= 5

    # 8. Admin exports users CSV
    res = client.get("/api/users/export", headers=admin_headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "Sarah Connor" in res.text

    # 9. Admin updates user
    res = client.patch(
        f"/api/users/{sarah['id']}",
        json={"salary": "$125,000"},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json()["salary"] == "$125,000"

    # 10. Knowledge sources list
    res = client.get("/api/sources", headers=emp_headers)
    assert res.status_code == 200
    sources = res.json()
    assert len(sources) >= 4
    # All sources have required frontend keys
    for s in sources:
        assert "id" in s
        assert "name" in s
        assert "description" in s
        assert "date" in s
        assert "uploadedBy" in s
        assert "version" in s
        assert "status" in s
        assert "size" in s
        assert "file" in s

    # 11. Admin uploads a knowledge source (text/policy)
    file_content = b"ConAI Travel Policy 2026: All flight bookings must be done 14 days in advance. Meals are reimbursed up to $80 per day."
    res = client.post(
        "/api/sources",
        data={
            "name": "Corporate Travel Guideline 2026",
            "description": "Updated travel guidelines",
            "status": "published",
        },
        files={"file": ("travel_guideline.txt", file_content, "text/plain")},
        headers=admin_headers,
    )
    assert res.status_code == 200
    uploaded_source = res.json()
    source_id = uploaded_source["id"]

    # 12. Check status and file download
    res = client.get(f"/api/sources/{source_id}/status", headers=emp_headers)
    assert res.status_code == 200
    assert res.json()["ingestionStatus"] in ["pending", "processing", "indexed"]

    res = client.get(f"/api/sources/{source_id}/file", headers=emp_headers)
    assert res.status_code == 200
    assert b"ConAI Travel Policy 2026" in res.content

    # 13. Sync Policy configuration
    res = client.post(
        f"/api/sources/{source_id}/sync-policy",
        json={"schedule": "0 2 * * *", "enabled": True},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json()["schedule"] == "0 2 * * *"

    # 14. AI Chat flow
    res = client.post(
        "/api/chat/sessions",
        json={"title": "Policy Inquiries"},
        headers=emp_headers,
    )
    assert res.status_code == 200
    session_id = res.json()["id"]

    # Send user question
    res = client.post(
        f"/api/chat/sessions/{session_id}/messages",
        json={"text": "What are the rules regarding MFA and security incidents?"},
        headers=emp_headers,
    )
    assert res.status_code == 200
    chat_result = res.json()
    messages = chat_result["messages"]
    assert len(messages) == 3  # initial greeting + user msg + ai reply
    assert messages[1]["from"] == "user"
    assert messages[2]["from"] == "assistant"
    assert "Information Security Policy" in messages[2]["text"]

    # 15. Message Threads (Admin <-> Employee)
    res = client.get("/api/threads", headers=emp_headers)
    assert res.status_code == 200
    emp_threads = res.json()
    assert len(emp_threads) >= 1
    thread_id = emp_threads[0]["id"]

    # Employee sends message
    res = client.post(
        f"/api/threads/{thread_id}/messages",
        json={"text": "Hi Admin, I have a question about my remote work equipment allowance."},
        headers=emp_headers,
    )
    assert res.status_code == 200

    # Admin checks notifications and threads
    res = client.get("/api/notifications", headers=admin_headers)
    assert res.status_code == 200
    notifs = res.json()
    assert len(notifs) >= 1
    notif_id = notifs[0]["id"]

    # Admin marks notification read
    res = client.post(f"/api/notifications/{notif_id}/read", headers=admin_headers)
    assert res.status_code == 200

    # Admin replies on thread
    res = client.post(
        f"/api/threads/{thread_id}/messages",
        json={"text": "Sure Marcus! You have up to $500 per year for equipment."},
        headers=admin_headers,
    )
    assert res.status_code == 200

    # 16. Dashboard stats
    res = client.get("/api/dashboard/stats", headers=admin_headers)
    assert res.status_code == 200
    stats = res.json()
    assert stats["totalSources"] >= 5
    assert stats["totalUsers"] >= 5
    assert stats["activeUsers"] >= 5

    # 17. Cleanup test user
    client.delete(f"/api/users/{sarah['id']}", headers=admin_headers)
    client.delete(f"/api/sources/{source_id}", headers=admin_headers)

    print("\n[ALL 17 END-TO-END PLATFORM TESTS PASSED SUCCESSFULLY!]")


if __name__ == "__main__":
    test_full_platform_flow()
