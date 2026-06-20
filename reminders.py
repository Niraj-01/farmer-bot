"""
Proactive daily reminders — THE differentiator vs a chatbot.
Run once a day (cron / Render scheduled job). For every onboarded farmer whose
task falls in the next 1-2 days, send a WhatsApp reminder via Twilio.

    python reminders.py            # send for real
    python reminders.py --dry      # just print what would be sent
"""
import os
import sys
from datetime import date, timedelta

import store
import schedule as sch
from helpers import weather_alert

DEFAULT_LANG = "mr"
LOOKAHEAD_DAYS = 2  # remind when a task is within this many days

REMINDER_HDR = {
    "mr": "🔔 आठवण ({crop})\nपुढील कामे:",
    "hi": "🔔 याद दिलाना ({crop})\nअगले काम:",
    "en": "🔔 Reminder ({crop})\nUpcoming tasks:",
}


def due_tasks(crop, sowing_date, today):
    sched = sch.build_schedule(crop, sowing_date)
    horizon = today + timedelta(days=LOOKAHEAD_DAYS)
    return [s for s in sched if today <= s["date_start"] <= horizon]


def build_reminder(farmer, today):
    lang = farmer.get("lang") or DEFAULT_LANG
    crop = farmer["crop"]
    sow = date.fromisoformat(farmer["sowing_date"])
    due = due_tasks(crop, sow, today)
    if not due:
        return None
    crop_name = sch.CROPS[crop][lang]
    lines = []
    for t in due:
        name = t.get(f"task_{lang}") or t["task"]
        qty = f" ({t['input_qty']})" if t["input_qty"] else ""
        lines.append(f"• *{t['date_start'].strftime('%d %b')}* — {name}{qty}")
    hdr = REMINDER_HDR.get(lang, REMINDER_HDR["mr"]).format(crop=crop_name)
    msg = hdr + "\n" + "\n".join(lines)
    alert = weather_alert(farmer.get("district", ""), lang)
    if alert:
        msg += "\n\n" + alert
    return msg


def send_whatsapp(to, body):
    from twilio.rest import Client
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_ = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")  # sandbox default
    Client(sid, token).messages.create(from_=from_, to=to, body=body)


def run(dry=False):
    today = date.today()
    farmers = store.all_active()
    print(f"{today}: checking {len(farmers)} farmer(s)...")
    sent = 0
    for f in farmers:
        # Rate limit: never message the same farmer twice in one day, even if
        # the cron is triggered more than once.
        if not dry and f.get("last_reminded") == today.isoformat():
            print(f"skip {f['phone']} (already reminded today)")
            continue
        msg = build_reminder(f, today)
        if not msg:
            continue
        if dry:
            print(f"\n--> {f['phone']}\n{msg}")
        else:
            try:
                send_whatsapp(f["phone"], msg)
                f["last_reminded"] = today.isoformat()
                store.save(f["phone"], f)
                print(f"sent to {f['phone']}")
            except Exception as e:
                print(f"failed {f['phone']}: {e}")
        sent += 1
    print(f"\nDone. {sent} reminder(s).")


if __name__ == "__main__":
    run(dry="--dry" in sys.argv)
