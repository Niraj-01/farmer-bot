# 🚀 Publishing — How to take this live

There are two levels. Pick based on how soon and how public you need it.

| Level | Who can use it | Time | Cost |
|---|---|---|---|
| **A. Live demo** (Twilio sandbox) | You + testers who first send a join code | ~30–60 min | Free |
| **B. Fully public** (WhatsApp Business API) | Any farmer, no join code | 3–10 days* | Paid per msg |

\* The delay in Level B is **Meta's business verification review** — outside anyone's control.

---

## LEVEL A — Live demo on a public URL (do this first)

### Step 1 — Put the code on GitHub (5 min)
```bash
cd /Users/niraj/farmer
git init && git add . && git commit -m "Farmer WhatsApp assistant"
# create an empty repo on github.com, then:
git remote add origin https://github.com/<you>/farmer-bot.git
git push -u origin main
```

### Step 2 — Deploy to Render (10 min, free)
1. Sign up at render.com (free).
2. **New → Blueprint** → pick your repo. It reads `render.yaml` and creates the
   web service + the daily reminder cron automatically.
3. You get a public URL like `https://farmer-whatsapp-bot.onrender.com`.
4. Open `https://<your-url>/demo` — the browser demo works immediately, no Twilio.

### Step 3 — Connect real WhatsApp via Twilio sandbox (15 min, free)
1. Sign up at twilio.com → **Messaging → Try it out → WhatsApp Sandbox**.
2. From your phone, send the join code (e.g. `join <two-words>`) to Twilio's number.
3. In sandbox settings, set **"When a message comes in"** to:
   `https://<your-url>/whatsapp`  (POST).
4. Add your Twilio keys in the Render dashboard (Environment tab):
   `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM=whatsapp:+14155238886`.
5. Message the sandbox number "hi" → the bot replies on real WhatsApp. ✅ **Live.**

Anyone you want to test must first send the join code — that's the only sandbox limit.

---

## LEVEL B — Fully public (any farmer, no join code)

This needs the **WhatsApp Business API** through Twilio (or Meta direct):
1. A **Meta Business account** + business verification (submit company docs).
2. A **WhatsApp sender** (a phone number) approved on the account.
3. **Message templates** approved by Meta for proactive sends (reminders).
4. Then point the same `/whatsapp` webhook at the production number.

The code does **not** change — only the number and credentials. The wait is Meta's
review (typically several days). Start this in parallel once the client says go.

---

## Production hardening (before real scale)
- **Database:** ✅ Done. `render.yaml` provisions a free **Postgres** database and
  wires `DATABASE_URL` into both the web service and the cron, so they share one
  store. `store.py` auto-detects: Postgres when `DATABASE_URL` is set, SQLite
  locally. No dashboard step needed for the DB.
- **Secrets:** never commit `.env`; set Twilio/weather/Claude keys in the Render dashboard.
- **Opt-out + rate limits:** ✅ Done. Farmers reply `stop` (or `बंद`/`थांबा`) to
  unsubscribe and `resume` to opt back in; the cron skips opted-out farmers and
  never messages anyone twice in the same day.
- **Agronomist sign-off** on `crops.csv` before farmers act on the advice.

---

## What I (Claude) can vs. can't do for you
- ✅ I made the code production-ready: `Procfile`, `render.yaml`, `.gitignore`, gunicorn.
- ✅ I can write/adjust any config, swap SQLite→Postgres, add features.
- ❌ I can't create your Twilio/Render/Meta accounts or enter payment — those need
  your identity and login. Steps above are exactly what to click.

**Fastest realistic path:** Level A today (≈1 hour with your accounts) → start Level B
verification in parallel → flip to the public number when Meta approves.
