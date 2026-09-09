from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from pwdlib import PasswordHash

from app.core.config import settings

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)
password_hash = PasswordHash.recommended()


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: str
    username: str


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(settings.JOB_DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute(
        "CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL)"
    )
    return connection


def _token(user: UserResponse) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode({"sub": user.id, "username": user.username, "exp": expires}, settings.JWT_SECRET_KEY, algorithm="HS256")


def _find_user(username: str) -> sqlite3.Row | None:
    with _connect() as connection:
        return connection.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> dict:
    user = UserResponse(id=str(uuid.uuid4()), username=payload.username)
    try:
        with _connect() as connection:
            connection.execute(
                "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (user.id, user.username, password_hash.hash(payload.password), datetime.now(timezone.utc).isoformat()),
            )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Username đã tồn tại.") from exc
    return {"access_token": _token(user), "token_type": "bearer", "user": user.model_dump()}


@router.post("/login", response_model=dict)
def login(form: OAuth2PasswordRequestForm = Depends()) -> dict:
    row = _find_user(form.username)
    if not row or not password_hash.verify(form.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Thông tin đăng nhập không hợp lệ.", headers={"WWW-Authenticate": "Bearer"})
    user = UserResponse(id=row["id"], username=row["username"])
    return {"access_token": _token(user), "token_type": "bearer", "user": user.model_dump()}


def current_user(token: str | None = Depends(oauth2_scheme)) -> UserResponse:
    if not token:
        if settings.AUTH_REQUIRED:
            raise HTTPException(status_code=401, detail="Yêu cầu đăng nhập.", headers={"WWW-Authenticate": "Bearer"})
        return UserResponse(id="local-dev", username="local-dev")
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        return UserResponse(id=str(payload["sub"]), username=str(payload.get("username", payload["sub"])))
    except (jwt.InvalidTokenError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Token không hợp lệ hoặc đã hết hạn.", headers={"WWW-Authenticate": "Bearer"}) from exc


@router.get("/me", response_model=UserResponse)
def me(user: UserResponse = Depends(current_user)) -> UserResponse:
    return user
