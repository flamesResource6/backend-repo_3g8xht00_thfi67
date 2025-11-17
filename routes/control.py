from fastapi import APIRouter, Depends, HTTPException
from sqlite_db import get_conn
from .auth import get_user_by_token

router = APIRouter(prefix="/control", tags=["control"])

@router.post("/toggle/{appliance_id}")
def toggle(appliance_id: int, user=Depends(get_user_by_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT is_on FROM appliances WHERE id=? AND user_id=?", (appliance_id, user["id"]))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, detail="Appliance not found")
    new_state = 0 if row[0] else 1
    cur.execute("UPDATE appliances SET is_on=? WHERE id=? AND user_id=?", (new_state, appliance_id, user["id"]))
    conn.commit()
    conn.close()
    return {"appliance_id": appliance_id, "is_on": bool(new_state)}

@router.post("/set/{appliance_id}")
def set_state(appliance_id: int, is_on: bool, user=Depends(get_user_by_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE appliances SET is_on=? WHERE id=? AND user_id=?", (1 if is_on else 0, appliance_id, user["id"]))
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(404, detail="Appliance not found")
    conn.commit()
    conn.close()
    return {"appliance_id": appliance_id, "is_on": is_on}
