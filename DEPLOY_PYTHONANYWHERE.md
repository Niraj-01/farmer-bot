# 🚀 Deploy on PythonAnywhere (no payment card needed)

Free "Beginner" account. Gives a permanent URL + a daily scheduled task, and the
web app + scheduled task share one disk so SQLite just works (no Postgres needed).

## 1. Sign up
→ https://www.pythonanywhere.com/registration/register/beginner/
Pick a username — it becomes your URL: `https://<username>.pythonanywhere.com`

## 2. Get the code (Bash console)
Dashboard → **Consoles → Bash**, then:
```bash
git clone https://github.com/Niraj-01/farmer-bot.git
cd farmer-bot
pip install --user flask twilio requests
```
(Skip gunicorn/psycopg2 — PythonAnywhere serves Flask its own way and we use SQLite.)

## 3. Create the web app
Dashboard → **Web → Add a new web app** → **Manual configuration** → **Python 3.10**.

Then on the Web tab set:
- **Source code:** `/home/<username>/farmer-bot`
- **WSGI configuration file:** click it and replace the contents with exactly:
  ```python
  import sys
  path = "/home/<username>/farmer-bot"
  if path not in sys.path:
      sys.path.insert(0, path)
  from app import app as application   # PythonAnywhere looks for `application`
  ```
- Click the green **Reload** button.

Open `https://<username>.pythonanywhere.com/demo` → the chat works immediately. ✅

## 4. Twilio webhook
Twilio sandbox → **When a message comes in**:
`https://<username>.pythonanywhere.com/whatsapp`  (POST)

Set your Twilio secrets — easiest is the Web tab → **Environment variables**:
`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`, `OPENWEATHER_API_KEY`.
Then **Reload** the web app.

## 5. Daily reminders (the cron)
Dashboard → **Tasks** → add a daily task at e.g. `06:00`:
```
cd /home/<username>/farmer-bot && python3 reminders.py
```
Free accounts get one daily scheduled task — exactly what we need. It reads the
same `farmers.db` the web app writes, so it sees everyone who registered in chat.

---
**Note on the free outbound whitelist:** Twilio (`api.twilio.com`) and OpenWeather
are allowed, so messaging + weather work. Anthropic (Claude phrasing) may be
blocked — that's fine, the bot falls back to sending the plain message.
