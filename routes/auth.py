from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
import secrets
from sqlite_db import get_conn, verify_password, _hash_password
from typing import Optional

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterBody(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginBody(BaseModel):
    email: EmailStr
    password: str

class UpdateMeBody(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None


def get_user_by_token(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1].strip()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email FROM users WHERE token=?", (token,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"id": row[0], "name": row[1], "email": row[2], "token": token}


@router.post("/register")
def register(body: RegisterBody):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email=?", (body.email.lower(),))
    if cur.fetchone():
        conn.close()
        raise HTTPException(400, detail="Email already registered")
    cur.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?,?,?, datetime('now'))",
        (body.name.strip(), body.email.lower(), _hash_password(body.password)),
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"id": user_id, "name": body.name, "email": body.email}


@router.post("/login")
def login(body: LoginBody):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, password_hash FROM users WHERE email=?", (body.email.lower(),))
    row = cur.fetchone()
    if not row or not verify_password(body.password, row[3]):
        conn.close()
        raise HTTPException(401, detail="Invalid credentials")
    token = secrets.token_hex(16)
    cur.execute("UPDATE users SET token=? WHERE id=?", (token, row[0]))
    conn.commit()
    conn.close()
    return {"token": token, "user": {"id": row[0], "name": row[1], "email": row[2]}}


@router.post("/logout")
def logout(user=Depends(get_user_by_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET token=NULL WHERE id=?", (user["id"],))
    conn.commit()
    conn.close()
    return {"message": "Logged out"}


@router.get("/me")
def me(user=Depends(get_user_by_token)):
    return user


@router.put("/me")
def update_me(body: UpdateMeBody, user=Depends(get_user_by_token)):
    conn = get_conn()
    cur = conn.cursor()
    if body.name:
        cur.execute("UPDATE users SET name=? WHERE id=?", (body.name.strip(), user["id"]))
    if body.password:
        cur.execute("UPDATE users SET password_hash=? WHERE id=?", (_hash_password(body.password), user["id"]))
    conn.commit()
    conn.close()
    return {"message": "Profile updated"}
