from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from sqlite_db import get_conn
from .auth import get_user_by_token

router = APIRouter(prefix="/energy", tags=["energy"])

class EnergyQuery(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    appliance_id: Optional[int] = None


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


@router.get("")
def get_energy(start: Optional[str] = None, end: Optional[str] = None, appliance_id: Optional[int] = None, user=Depends(get_user_by_token)):
    start_dt = _parse_dt(start)
    end_dt = _parse_dt(end)
    if end_dt is None:
        end_dt = datetime.utcnow()
    if start_dt is None:
        start_dt = end_dt - timedelta(days=1)
    conn = get_conn()
    cur = conn.cursor()
    params = [user["id"], start_dt.isoformat(), end_dt.isoformat()]
    q = "SELECT timestamp, consumption, voltage, current, frequency, appliance_id FROM energy_consumption WHERE user_id=? AND timestamp BETWEEN ? AND ?"
    if appliance_id:
        q += " AND appliance_id=?"
        params.append(appliance_id)
    q += " ORDER BY timestamp ASC"
    cur.execute(q, params)
    rows = [
        dict(
            timestamp=r[0], consumption=r[1], voltage=r[2], current=r[3], frequency=r[4], appliance_id=r[5]
        )
        for r in cur.fetchall()
    ]
    conn.close()
    return rows


@router.get("/summary")
def summary(period: str = Query("day", enum=["hour", "day", "week", "month"]), user=Depends(get_user_by_token)):
    conn = get_conn()
    cur = conn.cursor()
    group_expr = {
        "hour": "substr(timestamp, 1, 13)",
        "day": "substr(timestamp, 1, 10)",
        "week": "strftime('%W', timestamp)",
        "month": "substr(timestamp, 1, 7)",
    }[period]
    cur.execute(
        f"SELECT {group_expr} as period, SUM(consumption) as total FROM energy_consumption WHERE user_id=? GROUP BY period ORDER BY period",
        (user["id"],),
    )
    rows = [dict(period=r[0], total=r[1]) for r in cur.fetchall()]
    conn.close()
    return rows


@router.get("/realtime")
def realtime(user=Depends(get_user_by_token)):
    # Return last 10 readings
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT timestamp, consumption, voltage, current, frequency FROM energy_consumption WHERE user_id=? ORDER BY timestamp DESC LIMIT 10",
        (user["id"],),
    )
    rows = [dict(timestamp=r[0], consumption=r[1], voltage=r[2], current=r[3], frequency=r[4]) for r in cur.fetchall()]
    conn.close()
    return list(reversed(rows))


@router.post("/ingest")
def ingest(data: list[dict], user=Depends(get_user_by_token)):
    # Bulk ingest readings
    if not isinstance(data, list) or len(data) == 0:
        raise HTTPException(400, detail="Provide a list of readings")
    conn = get_conn()
    cur = conn.cursor()
    for item in data:
        cur.execute(
            "INSERT INTO energy_consumption (user_id, appliance_id, timestamp, consumption, voltage, current, frequency) VALUES (?,?,?,?,?,?,?)",
            (
                user["id"],
                item.get("appliance_id"),
                item.get("timestamp") or datetime.utcnow().isoformat(),
                float(item.get("consumption", 0)),
                float(item.get("voltage") or 230.0),
                float(item.get("current") or 0.0),
                float(item.get("frequency") or 50.0),
            ),
        )
    conn.commit()
    conn.close()
    return {"inserted": len(data)}
