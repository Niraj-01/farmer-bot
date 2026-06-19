"""
Crop schedule engine.
Takes crop + sowing date, returns a full dated task calendar from crops.csv.
This is the 'AI brain' — a lookup table + date math. No ML needed.
"""
import csv
import os
from datetime import date, datetime, timedelta

CROP_FILE = os.path.join(os.path.dirname(__file__), "crops.csv")

# Display names for the WhatsApp list buttons (crop key -> labels)
CROPS = {
    "cotton": {"en": "Cotton", "mr": "कापूस", "hi": "कपास"},
    "soybean": {"en": "Soybean", "mr": "सोयाबीन", "hi": "सोयाबीन"},
    "wheat": {"en": "Wheat", "mr": "गहू", "hi": "गेहूं"},
    "tur": {"en": "Tur (Pigeon pea)", "mr": "तूर", "hi": "तुअर"},
}


def load_tasks(crop):
    """Return all task rows for a crop, sorted by days-after-sowing."""
    rows = []
    with open(CROP_FILE, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["crop"].strip().lower() == crop.lower():
                r["das_start"] = int(r["das_start"])
                r["das_end"] = int(r["das_end"])
                rows.append(r)
    return sorted(rows, key=lambda x: x["das_start"])


def build_schedule(crop, sowing_date):
    """Attach real calendar dates to each task. Returns list of dicts."""
    tasks = load_tasks(crop)
    schedule = []
    for t in tasks:
        start = sowing_date + timedelta(days=t["das_start"])
        end = sowing_date + timedelta(days=t["das_end"])
        schedule.append({**t, "date_start": start, "date_end": end})
    return schedule


def harvest_date(crop, sowing_date):
    sched = build_schedule(crop, sowing_date)
    harvest = [s for s in sched if s["stage"].lower() == "harvest"]
    if harvest:
        return harvest[0]["date_start"]
    return sched[-1]["date_start"] if sched else None


def current_stage(crop, sowing_date, today=None):
    today = today or date.today()
    das = (today - sowing_date).days
    sched = build_schedule(crop, sowing_date)
    stage = "Pre-sowing"
    for s in sched:
        if das >= s["das_start"]:
            stage = s["stage"]
    return stage, das


def next_tasks(crop, sowing_date, today=None, n=3, lang="mr"):
    """The upcoming N tasks the farmer should prepare for."""
    today = today or date.today()
    sched = build_schedule(crop, sowing_date)
    upcoming = [s for s in sched if s["date_end"] >= today]
    out = []
    for s in upcoming[:n]:
        name = s.get(f"task_{lang}") or s["task"]
        qty = f" ({s['input_qty']})" if s["input_qty"] else ""
        out.append({
            "date": s["date_start"],
            "text": name + qty,
            "stage": s["stage"],
        })
    return out


def parse_date(text):
    """Best-effort parse of a farmer-typed/spoken date. Returns date or None."""
    text = text.strip()
    fmts = ["%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y",
            "%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%d %b", "%d %B"]
    for fmt in fmts:
        try:
            d = datetime.strptime(text, fmt).date()
            if d.year == 1900:  # format without year -> assume current year
                d = d.replace(year=date.today().year)
            return d
        except ValueError:
            continue
    return None


if __name__ == "__main__":
    # Quick demo
    sow = date(2026, 6, 1)
    print("Cotton sown:", sow)
    print("Harvest ~", harvest_date("cotton", sow))
    print("Stage today:", current_stage("cotton", sow))
    print("\nNext 3 tasks:")
    for t in next_tasks("cotton", sow):
        print(f"  {t['date']}  —  {t['text']}")
