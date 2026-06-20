"""
Farmer store. Persists sessions so the reminder cron can reach farmers across
restarts and across separate instances.

Two backends, same interface (init / get / save / all_active):
  * Production: Postgres, when DATABASE_URL is set (Render wires this in for
    BOTH the web service and the cron, so they share one database).
  * Local dev: zero-config SQLite — just creates farmers.db next to this file.

The SQL below (TEXT/INTEGER columns, ON CONFLICT upsert) is compatible with
both engines, so only the connection + placeholder style differ.
"""
import json
import os
import sqlite3
from datetime import date

DATABASE_URL = os.getenv("DATABASE_URL")
SQLITE_PATH = os.path.join(os.path.dirname(__file__), "farmers.db")

if DATABASE_URL:
    import psycopg2
    import psycopg2.extras

    PH = "%s"  # Postgres parameter placeholder

    def _conn():
        return psycopg2.connect(DATABASE_URL)

    def _cursor(conn):
        return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
else:
    PH = "?"  # SQLite parameter placeholder

    def _conn():
        c = sqlite3.connect(SQLITE_PATH)
        c.row_factory = sqlite3.Row
        return c

    def _cursor(conn):
        return conn.cursor()


def _run(sql, params=(), fetch=None):
    """Run one statement, commit, return dict rows (or None)."""
    conn = _conn()
    try:
        cur = _cursor(conn)
        cur.execute(sql, params)
        result = None
        if fetch == "one":
            row = cur.fetchone()
            result = dict(row) if row else None
        elif fetch == "all":
            result = [dict(r) for r in cur.fetchall()]
        conn.commit()
        return result
    finally:
        conn.close()


def init():
    _run(
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
    d = _run(f"SELECT * FROM farmers WHERE phone={PH}", (phone,), fetch="one")
    if not d:
        return {"step": "start", "phone": phone}
    if d.get("data"):
        d.update(json.loads(d["data"]))
    return d


def save(phone, session):
    init()
    extra = {k: v for k, v in session.items()
             if k not in ("phone", "step", "crop", "sowing_date",
                          "district", "irrigation", "lang")}
    _run(
        f"""INSERT INTO farmers (phone, step, crop, sowing_date, district,
             irrigation, lang, data)
           VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})
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
    """Onboarded farmers who have NOT opted out of reminders.

    `opted_out` is stored inside the JSON `data` column, so we filter in Python
    after expanding it (keeps the schema unchanged across SQLite/Postgres).
    """
    init()
    rows = _run(
        "SELECT * FROM farmers WHERE step='done' AND sowing_date IS NOT NULL",
        fetch="all",
    ) or []
    out = []
    for r in rows:
        if r.get("data"):
            r.update(json.loads(r["data"]))
        if not r.get("opted_out"):
            out.append(r)
    return out
