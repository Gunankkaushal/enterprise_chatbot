from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from services.database.db_connection import get_db
from services.database.models import User, Department
from routes.auth import require_admin

createrouter = APIRouter(
    prefix="/create",
    tags=["Create Departments"]
)

@createrouter.post("/")
def create_department(name: str = Form(...), db: Session = Depends(get_db), admin_user: User = Depends(require_admin)):

    existing_department = db.query(Department).filter(
        Department.name.ilike(name)
    ).first()

    if existing_department:

        raise HTTPException(
            status_code=409,
            detail="Department already exists"
        )

    new_department = Department(
        name=name.strip()
    )

    db.add(new_department)

    db.commit()

    db.refresh(new_department)

    return {
        "message": "Department created successfully",
        "department": {
            "id": new_department.id,
            "name": new_department.name
        }
    }