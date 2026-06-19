"""
Tiny SQLite store for farmers. Replaces the in-memory SESSIONS dict so that
the reminder cron can reach farmers across restarts. Still zero-config: it just
creates farmers.db next to this file.
"""
import json
import os
import sqlite3
from datetime import date

DB = os.path.join(os.path.dirname(__file__), "farmers.db")


def _conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS farmers (
                phone TEXT PRIMARY KEY,
                step TEXT,
                crop TEXT,
                sowing_date TEXT,
                district TEXT,
                irrigation INTEGER,
                lang TEXT,
                data TEXT
            )"""
        )


def get(phone):
    init()
    with _conn() as c:
        row = c.execute("SELECT * FROM farmers WHERE phone=?", (phone,)).fetchone()
        if not row:
            return {"step": "start", "phone": phone}
        d = dict(row)
        if d.get("data"):
            d.update(json.loads(d["data"]))
        return d


def save(phone, session):
    init()
    extra = {k: v for k, v in session.items()
             if k not in ("phone", "step", "crop", "sowing_date",
                          "district", "irrigation", "lang")}
    with _conn() as c:
        c.execute(
            """INSERT INTO farmers (phone, step, crop, sowing_date, district,
                 irrigation, lang, data)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(phone) DO UPDATE SET
                 step=excluded.step, crop=excluded.crop,
                 sowing_date=excluded.sowing_date, district=excluded.district,
                 irrigation=excluded.irrigation, lang=excluded.lang,
                 data=excluded.data""",
            (phone, session.get("step"), session.get("crop"),
             session.get("sowing_date"), session.get("district"),
             int(bool(session.get("irrigation"))), session.get("lang", "mr"),
             json.dumps(extra)),
        )


def all_active():
    """Farmers who finished onboarding (have a crop + sowing date)."""
    init()
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM farmers WHERE step='done' AND sowing_date IS NOT NULL"
        ).fetchall()
        return [dict(r) for r in rows]
