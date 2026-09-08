"""Users router — admin-only for writes, read for self."""
import csv
import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth import AdminUser, CurrentUser, hash_password
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserOut, UserPermissions, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])

_ROLE_PERMISSIONS = {
    "ADMIN": UserPermissions(canManageUsers=True, canManagePolicies=True),
    "EMPLOYEE": UserPermissions(canManageUsers=False, canManagePolicies=False),
}
_COLOR_CYCLE = ["blue", "violet", "amber", "teal", "rose", "emerald", "sky"]


def _to_out(user: User) -> UserOut:
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


@router.get("", response_model=list[UserOut])
def list_users(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    users = db.query(User).all()
    return [_to_out(u) for u in users]


@router.post("", response_model=UserOut)
def create_user(
    body: UserCreate,
    admin: AdminUser,
    db: Session = Depends(get_db),
):
    existing = (
        db.query(User)
        .filter((User.email == body.email) | (User.employee_id == body.employeeId))
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Email or Employee ID already in use.")

    import datetime
    initials = "".join(p[0] for p in body.name.split() if p)[:2].upper()
    user_count = db.query(User).count()
    color = body.color or _COLOR_CYCLE[user_count % len(_COLOR_CYCLE)]
    joined = datetime.datetime.now().strftime("%b %d, %Y")

    user = User(
        name=body.name,
        initials=initials,
        employee_id=body.employeeId,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
        department=body.department,
        salary=body.salary,
        status="Active",
        joined=joined,
        color=color,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _to_out(user)


@router.get("/export")
def export_users(
    admin: AdminUser,
    db: Session = Depends(get_db),
):
    """Download all users as CSV — matches the frontend export button."""
    users = db.query(User).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Employee ID", "Email", "Role", "Department", "Salary", "Status", "Joined Date"])
    for u in users:
        writer.writerow([u.name, u.employee_id, u.email, u.role, u.department, u.salary, u.status, u.joined])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=conai-users.csv"},
    )


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return _to_out(user)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdate,
    admin: AdminUser,
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    if body.name:
        user.initials = "".join(p[0] for p in body.name.split() if p)[:2].upper()
    db.commit()
    db.refresh(user)
    return _to_out(user)


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    admin: AdminUser,
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account.")
    db.delete(user)
    db.commit()
    return {"detail": "User deleted."}
