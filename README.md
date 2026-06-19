# 🌾 Farmer WhatsApp Assistant (MVP)

A WhatsApp bot that turns a **sowing date** into a **personalized, dated farming
calendar** — delivered by text or voice, in Marathi/Hindi/English.

> A chatbot answers questions. This one tells the farmer *what to do, before they
> ask*, in their own voice.

## How it works
1. Farmer messages the WhatsApp number.
2. Bot asks **4 things**: crop → sowing date → district → irrigation.
3. Bot replies with: confirmation + expected harvest date, the **next 3 dated
   tasks**, and a **weather alert**. Then it can keep giving "what's next".

The "brain" is `crops.csv` — a lookup table of *Crop + Task + Days-After-Sowing*
sourced from agricultural-university Package of Practices. No model training needed.

## Files
| File | Purpose |
|---|---|
| `crops.csv` | The crop knowledge table (cotton, soybean, wheat, tur) |
| `schedule.py` | Turns sowing date + crop into dated tasks |
| `app.py` | WhatsApp webhook + 4-question conversation flow |
| `helpers.py` | Voice→text (Bhashini/Whisper), weather, Claude phrasing (all optional) |
| `store.py` | SQLite store for farmers (so reminders survive restarts) |
| `reminders.py` | **Proactive daily cron** — messages farmers before each task |
| `PITCH.md` | Slide-by-slide pitch deck outline for the client |

## Setup (≈15 min)

```bash
cd /Users/niraj/farmer
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 1. Test the engine alone (no WhatsApp needed):
python schedule.py

# 2. Run the bot server:
python app.py        # serves on http://localhost:5000
# On macOS port 5000 is used by AirPlay — use:  PORT=5001 python app.py
```

### Browser demo (no Twilio needed — best fallback for the pitch)
Open **http://localhost:5001/demo** — a WhatsApp-style chat in the browser that
talks to the exact same logic. Tap the chips (hi → 1 → date → district → 1) to
show the full flow live, even with no internet/Twilio.

### Connect to WhatsApp (Twilio Sandbox — fastest path)
1. Create a free account at twilio.com → **Messaging → Try it out → WhatsApp Sandbox**.
2. From your phone, send the join code (e.g. `join <word-word>`) to the Twilio
   sandbox number. This connects your phone.
3. Expose your local server so Twilio can reach it:
   ```bash
   # install ngrok, then:
   ngrok http 5000
   ```
4. In the Twilio Sandbox settings, set **"When a message comes in"** to:
   `https://<your-ngrok-id>.ngrok.io/whatsapp`  (method: POST)
5. Message the sandbox number "hi" — the bot replies. Done. ✅

### Optional power-ups (.env)
Copy `.env.example` → `.env` and add keys for live weather, voice
transcription (Whisper/Bhashini), and Claude phrasing. Everything works without
them using safe fallbacks, so your demo never breaks.

## Demo script (for the client pitch)
1. Send **"hi"** → bot greets, shows crop list.
2. Tap/type **1** (Cotton).
3. Send a **voice note**: *"मी १ जून ला कापूस लावला"* (or type `01-06-2026`).
4. Type district: **Akola**.
5. Tap **1** (irrigation: yes).
6. 💥 Bot instantly returns the harvest date, next 3 dated tasks, and the rain alert.
7. Type **"पुढे"** → it shows the current growth stage + next tasks.

**The 3 wow moments to call out:** (a) it understood a *voice note*, (b) it gave
*exact dates* not generic advice, (c) it *changed the plan* because of weather.

## Proactive reminders (the killer feature) — already built
`reminders.py` finds every onboarded farmer with a task due in the next 2 days
and WhatsApps them automatically.
```bash
python reminders.py --dry    # preview what would be sent
python reminders.py          # send for real (needs Twilio keys)
```
Schedule it once a day with cron, or a Render/Railway scheduled job:
```
0 6 * * *  cd /Users/niraj/farmer && venv/bin/python reminders.py
```

## Next steps after MVP
- Disease detection: farmer sends a leaf photo → image model.
- Bhashini voice is wired in `helpers.py` — just add the keys in `.env`.
- Add more crops/regions with an agronomist; add market prices & govt schemes.
