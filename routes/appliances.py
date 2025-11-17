from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from sqlite_db import get_conn
from .auth import get_user_by_token

router = APIRouter(prefix="/appliances", tags=["appliances"])

class ApplianceBody(BaseModel):
    name: str
    type: Optional[str] = None
    power_rating: Optional[float] = 0
    room: Optional[str] = None

class ApplianceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    power_rating: Optional[float] = None
    room: Optional[str] = None
    is_on: Optional[bool] = None


@router.get("")
def list_appliances(user=Depends(get_user_by_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, type, is_on, power_rating, room FROM appliances WHERE user_id=? ORDER BY id DESC", (user["id"],))
    rows = [dict(id=r[0], name=r[1], type=r[2], is_on=bool(r[3]), power_rating=r[4], room=r[5]) for r in cur.fetchall()]
    conn.close()
    return rows


@router.post("")
def create_appliance(body: ApplianceBody, user=Depends(get_user_by_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO appliances (user_id, name, type, power_rating, room, created_at) VALUES (?,?,?,?,?, datetime('now'))",
        (user["id"], body.name, body.type, body.power_rating or 0, body.room),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"id": new_id, **body.model_dump()}


@router.get("/{appliance_id}")
def get_appliance(appliance_id: int, user=Depends(get_user_by_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, type, is_on, power_rating, room FROM appliances WHERE id=? AND user_id=?", (appliance_id, user["id"]))
    r = cur.fetchone()
    conn.close()
    if not r:
        raise HTTPException(404, detail="Not found")
    return dict(id=r[0], name=r[1], type=r[2], is_on=bool(r[3]), power_rating=r[4], room=r[5])


@router.put("/{appliance_id}")
def update_appliance(appliance_id: int, body: ApplianceUpdate, user=Depends(get_user_by_token)):
    conn = get_conn()
    cur = conn.cursor()
    fields = []
    values = []
    for key, val in body.model_dump(exclude_unset=True).items():
        if key == "is_on":
            fields.append("is_on=?")
            values.append(1 if val else 0)
        else:
            fields.append(f"{key}=?")
            values.append(val)
    if not fields:
        conn.close()
        return {"message": "No changes"}
    values.extend([appliance_id, user["id"]])
    cur.execute(f"UPDATE appliances SET {', '.join(fields)} WHERE id=? AND user_id=?", values)
    conn.commit()
    conn.close()
    return {"message": "Updated"}


@router.delete("/{appliance_id}")
def delete_appliance(appliance_id: int, user=Depends(get_user_by_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM appliances WHERE id=? AND user_id=?", (appliance_id, user["id"]))
    conn.commit()
    conn.close()
    return {"message": "Deleted"}
