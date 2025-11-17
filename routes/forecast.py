from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta
import math
from sqlite_db import get_conn
from .auth import get_user_by_token

router = APIRouter(prefix="/forecast", tags=["forecast"])

class ForecastRequest(BaseModel):
    horizon_hours: int = 24

class ForecastPoint(BaseModel):
    timestamp: str
    consumption: float

class ForecastResponse(BaseModel):
    points: List[ForecastPoint]

@router.post("")
def forecast(req: ForecastRequest, user=Depends(get_user_by_token)):
    # naive baseline forecast using last 24h average + sinusoidal daily pattern to simulate LSTM output
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT timestamp, consumption FROM energy_consumption WHERE user_id=? ORDER BY timestamp DESC LIMIT 24",
        (user["id"],),
    )
    recent = cur.fetchall()
    conn.close()
    base = sum([r[1] for r in recent]) / len(recent) if recent else 0.08

    now = datetime.utcnow()
    points = []
    for i in range(req.horizon_hours):
        t = now + timedelta(hours=i + 1)
        # Add a diurnal sinusoid pattern
        daily = 0.02 * (1 + math.sin((t.hour / 24) * 2 * math.pi))
        pred = max(0.01, base + daily)
        points.append(dict(timestamp=t.isoformat(), consumption=round(pred, 4)))

    return {"points": points}
