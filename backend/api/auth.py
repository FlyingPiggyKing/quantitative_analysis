"""Authentication API routes."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from backend.services.user_service import UserService
from backend.services.auth_service import create_access_token, decode_token
from backend.services.db_migration import get_db_connection

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    password: str
    captcha_id: int
    captcha_code: str


class LoginRequest(BaseModel):
    username: str
    password: str
    captcha_id: int
    captcha_code: str


def verify_captcha(captcha_id: int, code: str) -> bool:
    """Verify CAPTCHA - imported here to avoid circular import."""
    from backend.services.captcha_service import CaptchaService
    return CaptchaService.verify_captcha(captcha_id, code)


@router.post("/register")
async def register(request: RegisterRequest):
    """Register a new user."""
    if not verify_captcha(request.captcha_id, request.captcha_code):
        raise HTTPException(status_code=400, detail="Invalid or expired CAPTCHA")

    result = UserService.create_user(request.username, request.password)
    if "error" in result:
        if result["error"] == "Username already taken":
            raise HTTPException(status_code=409, detail=result["error"])
        raise HTTPException(status_code=400, detail=result["error"])

    return {"message": "User registered successfully", "user": result}


@router.post("/login")
async def login(request: LoginRequest):
    """Login and get JWT token."""
    if not verify_captcha(request.captcha_id, request.captcha_code):
        raise HTTPException(status_code=400, detail="Invalid or expired CAPTCHA")

    user = UserService.get_user_by_username(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not UserService.verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token, jti = create_access_token(user["id"], user["username"])

    # Store session
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        cursor.execute(
            "INSERT INTO user_sessions (user_id, token_jti, expires_at) VALUES (?, ?, ?)",
            (user["id"], jti, expires_at)
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "token": token,
        "user": {"id": user["id"], "username": user["username"]},
    }


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """Logout and invalidate token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Remove session
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_sessions WHERE token_jti = ?", (payload["jti"],))
        conn.commit()
    finally:
        conn.close()

    return {"message": "Logged out successfully"}


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Dependency to get current authenticated user from token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Verify session exists
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT user_id FROM user_sessions WHERE token_jti = ? AND expires_at > ?",
            (payload["jti"], datetime.now(timezone.utc).isoformat())
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Session expired")
    finally:
        conn.close()

    return {"user_id": int(payload["sub"]), "username": payload["username"]}
