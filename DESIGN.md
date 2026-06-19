# 🏗️ System Design — Farmer WhatsApp Assistant

## Design goals (what drove every decision)
1. **Reach the actual user** — non-literate farmers, no smartphone apps → **WhatsApp + voice**.
2. **Trustworthy advice** — wrong farming advice is harmful → **verified agronomy data, not a free-form LLM**.
3. **Proactive, not reactive** — push reminders, don't wait to be asked.
4. **Demo-proof** — every external dependency degrades gracefully; nothing crashes if a key is missing.
5. **2-day MVP, clean path to production.**

## Chosen architecture

```
        Farmer (text or voice note, Marathi/Hindi/English)
                         │  WhatsApp
                         ▼
            ┌─────────────────────────┐
            │  Twilio WhatsApp API     │  (sandbox for pilot → Business API for prod)
            └────────────┬────────────┘
                         │ webhook POST /whatsapp
                         ▼
   ┌──────────────────────────────────────────────┐
   │            app.py  (Flask)                     │
   │  4-question dialog state machine               │
   │   crop → date → district → irrigation          │
   └───┬───────────┬───────────┬───────────┬────────┘
       │           │           │           │
       ▼           ▼           ▼           ▼
   helpers.py   schedule.py  helpers.py  store.py
   ASR (voice)  crop calendar weather    SQLite
   Bhashini/    crops.csv +   OpenWeather farmers.db
   Whisper      date math
                   │
                   ▼
            helpers.py → Claude (warm Marathi phrasing, optional)
                   │
                   ▼
            WhatsApp reply: harvest date + next 3 tasks + alert

   ── separately, once a day ──
   reminders.py (cron) → reads store.py → sends proactive reminders
```

## Why these choices (and what we rejected)

| Decision | Chosen | Rejected | Why |
|---|---|---|---|
| Channel | WhatsApp | Native app / SMS | Farmers have WhatsApp, not apps; SMS can't do voice/images |
| WhatsApp provider | Twilio sandbox (pilot) | Meta Cloud API direct | Live in minutes; verification is slow for a 2-day MVP |
| "Brain" | Rules + CSV lookup | Pure LLM answering | Agronomy must be correct & auditable, not hallucinated |
| LLM role | Parsing + phrasing only | LLM decides the schedule | Keep AI where it's safe; keep advice deterministic |
| Voice | Bhashini (prod) / Whisper (fallback) | English-only ASR | Bhashini is free, govt, best for Marathi/Hindi |
| Storage | SQLite | Postgres/Redis now | Zero-config for MVP; swap later, same interface |
| State | Server-side dialog state machine | Stateless LLM "agent" | Predictable, cheap, debuggable |

## The data model (`crops.csv`)
One row = one task: `crop, stage, task, task_mr, task_hi, das_start, das_end, input_qty, notes`.
`das` = days after sowing. The whole engine = `sowing_date + das → calendar date`.
**Adding a crop or fixing a date = editing this file. No code, no retraining.**

## Components
- **app.py** — webhook + dialog state machine (`crop → date → district → irrigation → done`).
- **schedule.py** — pure functions: `build_schedule`, `harvest_date`, `current_stage`, `next_tasks`, `parse_date`.
- **helpers.py** — external I/O, all optional with fallbacks: `transcribe_voice` (Bhashini→Whisper), `weather_alert` (OpenWeather→canned), `phrase_with_claude` (→raw text).
- **store.py** — SQLite persistence so reminders survive restarts.
- **reminders.py** — daily cron; finds tasks due ≤2 days out, sends WhatsApp.
- **web_demo** (in app.py) — `/demo` browser chat to show it working without Twilio.

## Scaling path (pilot → production)
1. Twilio sandbox → **WhatsApp Business API** (verified number, templates for proactive sends).
2. SQLite → **Postgres**; add per-farmer history & feedback.
3. Whisper → **Bhashini** for all ASR; add **Text-to-Speech** so replies are spoken too.
4. Add **disease detection** (leaf photo → image model), **market prices** (e-NAM), **govt schemes**.
5. Crop data validated & expanded with an **agronomist**; region/soil variants.
6. Reminders cron → managed scheduler (Render/Railway/Cloud cron); observability + opt-out.

## Security / privacy notes
- Store only phone + farm basics; no sensitive PII.
- Per-farmer opt-out; rate-limit sends; secrets in `.env`, never in code.
- Always show advice as guidance; agronomist-validated content only.
