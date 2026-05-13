import os
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from jwt.exceptions import InvalidTokenError

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from sqlalchemy.orm import Session

from passlib.context import CryptContext
from dotenv import load_dotenv

from services.database.db_connection import get_db
from services.database.db_connection import Base, engine
from services.database.models import User, Department
from services.database.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token
)

logger = logging.getLogger(__name__)

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise ValueError("SECRET_KEY not found in environment.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

Base.metadata.create_all(bind=engine)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

authrouter = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password
    )


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:

    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    try:
        encoded_jwt = jwt.encode(
            to_encode,
            SECRET_KEY,
            algorithm=ALGORITHM
        )

        return encoded_jwt

    except Exception as e:

        logger.error(f"JWT encode error: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail="Could not create access token"
        )


def get_current_user(res: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)
):

    token = res.credentials

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = int(payload.get("sub"))

        user = db.query(User).filter(
            User.id == user_id
        ).first()

        if not user:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )

        return user

    except InvalidTokenError:

        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials"
        )


def require_admin(current_user: User = Depends(get_current_user)):

    if not current_user.is_admin:

        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current_user


@authrouter.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)) -> Any:

    existing_user = db.query(User).filter(
        User.email == user.email
    ).first()

    if existing_user:

        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    if user.is_admin and user.department_id is not None:

        raise HTTPException(
            status_code=400,
            detail="Admins cannot belong to a department"
        )

    if not user.is_admin and user.department_id is None:

        raise HTTPException(
            status_code=400,
            detail="Department required for users"
        )

    if user.department_id is not None:

        department = db.query(Department).filter(
            Department.id == user.department_id
        ).first()

        if not department:

            raise HTTPException(
                status_code=404,
                detail="Department not found"
            )

    try:

        hashed_pwd = get_password_hash(user.password)

        new_user = User(
            email=user.email,
            hashed_password=hashed_pwd,
            is_admin=user.is_admin,
            department_id=user.department_id
        )

        db.add(new_user)

        db.commit()

        db.refresh(new_user)

        return new_user

    except Exception as e:

        db.rollback()

        logger.error(f"Registration error: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail="Registration failed"
        )


@authrouter.post("/login", response_model=Token)
def login_user(user: UserLogin, db: Session = Depends(get_db)) -> Any:

    db_user = db.query(User).filter(
        User.email == user.email
    ).first()

    if not db_user or not verify_password(
        user.password,
        db_user.hashed_password
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = create_access_token({
        "sub": str(db_user.id),
        "is_admin": db_user.is_admin,
        "department_id": db_user.department_id
    })

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }