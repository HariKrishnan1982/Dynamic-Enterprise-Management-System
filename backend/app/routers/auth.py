"""Auth router: signup, login, logout, me."""
import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import (
    CurrentUser,
    create_access_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models import MessageThread, ThreadMessage, User
from app.schemas import LoginRequest, SignupRequest, TokenResponse, UserOut, UserPermissions

router = APIRouter(prefix="/api/auth", tags=["auth"])

_ROLE_PERMISSIONS = {
    "ADMIN": UserPermissions(canManageUsers=True, canManagePolicies=True),
    "EMPLOYEE": UserPermissions(canManageUsers=False, canManagePolicies=False),
}

_COLOR_CYCLE = ["blue", "violet", "amber", "teal", "rose", "emerald", "sky"]


def _user_to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        name=user.name,
        initials=user.initials,
        employeeId=user.employee_id,
        email=user.email,
        role=user.role,
        department=user.department,
        salary=user.salary,
        status=user.status,
        joined=user.joined,
        color=user.color,
        permissions=_ROLE_PERMISSIONS.get(user.role, _ROLE_PERMISSIONS["EMPLOYEE"]),
    )


@router.post("/signup")
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    existing = (
        db.query(User)
        .filter((User.email == body.identifier) | (User.employee_id == body.employeeId))
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Email or Employee ID already registered.")

    initials = "".join(p[0] for p in body.name.split() if p)[:2].upper()
    user_count = db.query(User).count()
    color = _COLOR_CYCLE[user_count % len(_COLOR_CYCLE)]
    joined = datetime.datetime.now().strftime("%b %d, %Y")

    user = User(
        name=body.name,
        initials=initials,
        employee_id=body.employeeId,
        email=body.identifier,
        hashed_password=hash_password(body.password),
        role=body.role,
        department=body.department or "General",
        salary="Pending",
        status="Active",
        joined=joined,
        color=color,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create a message thread for employees
    if user.role == "EMPLOYEE":
        thread = MessageThread(employee_id=user.id)
        db.add(thread)
        db.flush()
        welcome = ThreadMessage(
            thread_id=thread.id,
            from_="assistant",
            text=f"Hi {user.name.split()[0]}, how can I help with a company policy today?",
            sender_name="ConAI Assistant",
        )
        db.add(welcome)
        db.commit()

    token = create_access_token(user.id, user.role)
    return {"access_token": token, "token_type": "bearer", "user": _user_to_out(user)}


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter((User.email == body.identifier) | (User.employee_id == body.identifier))
        .first()
    )
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    token = create_access_token(user.id, user.role)
    return {"access_token": token, "token_type": "bearer", "user": _user_to_out(user)}


@router.post("/logout")
def logout(current_user: CurrentUser):
    # JWT is stateless; client drops the token. Return confirmation.
    return {"detail": "Logged out successfully."}


@router.get("/me", response_model=None)
def me(current_user: CurrentUser):
    return _user_to_out(current_user)
