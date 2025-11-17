import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent / "smartenergy.db"

SCHEMA_SQL = {
    "users": (
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            token TEXT,
            created_at TEXT NOT NULL
        );
        """
    ),
    "appliances": (
        """
        CREATE TABLE IF NOT EXISTS appliances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            type TEXT,
            is_on INTEGER DEFAULT 0,
            power_rating REAL DEFAULT 0,
            room TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
    ),
    "energy_consumption": (
        """
        CREATE TABLE IF NOT EXISTS energy_consumption (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            appliance_id INTEGER,
            timestamp TEXT NOT NULL,
            consumption REAL NOT NULL,
            voltage REAL,
            current REAL,
            frequency REAL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(appliance_id) REFERENCES appliances(id)
        );
        """
    ),
}


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db_with_sample_data():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_conn()
    cur = conn.cursor()

    # Create schema
    for ddl in SCHEMA_SQL.values():
        cur.execute(ddl)

    # Seed a user if none exists
    cur.execute("SELECT COUNT(*) as c FROM users")
    if cur.fetchone()[0] == 0:
        now = datetime.utcnow().isoformat()
        cur.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (?,?,?,?)",
            ("Demo User", "demo@smartenergy.ai", _hash_password("password"), now),
        )
        user_id = cur.lastrowid
        # Seed appliances
        appliances = [
            (user_id, "Air Conditioner", "HVAC", 0, 1500.0, "Living Room"),
            (user_id, "Refrigerator", "Kitchen", 1, 200.0, "Kitchen"),
            (user_id, "Water Heater", "Utility", 0, 3000.0, "Basement"),
        ]
        for a in appliances:
            cur.execute(
                "INSERT INTO appliances (user_id, name, type, is_on, power_rating, room, created_at) VALUES (?,?,?,?,?,?,?)",
                (*a, now),
            )

        # Seed 7 days of hourly energy data
        cur.execute("SELECT id FROM appliances WHERE user_id=?", (user_id,))
        app_ids = [r[0] for r in cur.fetchall()]
        base_time = datetime.utcnow() - timedelta(days=7)
        for h in range(7 * 24):
            t = base_time + timedelta(hours=h)
            for app_id in app_ids:
                # simple synthetic consumption pattern
                hour = t.hour
                base = 0.05 if app_id != app_ids[0] else (0.1 if 10 <= hour <= 18 else 0.02)
                consumption = max(0.01, base + (0.01 if hour % 3 == 0 else 0))
                cur.execute(
                    "INSERT INTO energy_consumption (user_id, appliance_id, timestamp, consumption, voltage, current, frequency) VALUES (?,?,?,?,?,?,?)",
                    (
                        user_id,
                        app_id,
                        t.isoformat(),
                        round(consumption, 4),
                        230.0,
                        round(consumption * 4.35, 3),
                        50.0,
                    ),
                )
    conn.commit()
    conn.close()


# Simple password hashing
import hashlib

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return _hash_password(password) == password_hash
