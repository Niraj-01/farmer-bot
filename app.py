"""
WhatsApp farming-assistant bot (Twilio Sandbox).
Flow:  language -> crop -> sowing date -> district -> irrigation -> full schedule.
Run:   python app.py    (then point Twilio sandbox webhook at /whatsapp)
"""
import os
from datetime import date

from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

import schedule as sch
import store
from helpers import transcribe_voice, weather_alert, phrase_with_claude

app = Flask(__name__)

# Sessions are persisted in SQLite/Postgres (store.py) so the reminder cron can
# reach farmers across restarts. Each farmer's language lives in their session.
DEFAULT_LANG = "mr"


def L(d, lang):
    """Pick the right language string from a {mr/hi/en: ...} dict (mr fallback)."""
    return d.get(lang, d["mr"])


# ---- language selection ----
ASK_LANG = (
    "🌐 भाषा निवडा / भाषा चुनें / Choose your language:\n\n"
    "1️⃣ मराठी (Marathi)\n2️⃣ हिंदी (Hindi)\n3️⃣ English"
)
LANG_BY_NUM = {"1": "mr", "2": "hi", "3": "en"}
LANG_BY_NAME = {
    "marathi": "mr", "मराठी": "mr",
    "hindi": "hi", "हिंदी": "hi", "हिन्दी": "hi",
    "english": "en", "इंग्रजी": "en", "अंग्रेजी": "en",
}
LANG_CHANGED = {
    "mr": "🌐 भाषा बदलली: मराठी ✅",
    "hi": "🌐 भाषा बदली गई: हिंदी ✅",
    "en": "🌐 Language set: English ✅",
}

WELCOME = {
    "mr": "नमस्कार! 🌾 मी तुमचा शेती मित्र. तुम्ही कोणतं पीक लावलं आहे?\n\n1️⃣ कापूस\n2️⃣ सोयाबीन\n3️⃣ गहू\n4️⃣ तूर\n\n(नंबर पाठवा किंवा बोला)",
    "hi": "नमस्ते! 🌾 मैं आपका खेती मित्र हूँ। आपने कौन सी फसल लगाई है?\n\n1️⃣ कपास\n2️⃣ सोयाबीन\n3️⃣ गेहूं\n4️⃣ तुअर\n\n(नंबर भेजें या बोलें)",
    "en": "Hello! 🌾 I am your farming assistant. Which crop did you sow?\n\n1️⃣ Cotton\n2️⃣ Soybean\n3️⃣ Wheat\n4️⃣ Tur\n\n(send a number or speak)",
}
CROP_BY_NUM = {"1": "cotton", "2": "soybean", "3": "wheat", "4": "tur"}

ASK_DATE = {
    "mr": "👍 छान! तुम्ही ते कधी लावलं? तारीख सांगा (उदा. 01-06-2026) किंवा व्हॉइस पाठवा.",
    "hi": "👍 अच्छा! आपने इसे कब बोया? तारीख बताएं (जैसे 01-06-2026) या वॉइस भेजें।",
    "en": "👍 Great! When did you sow it? Send date (e.g. 01-06-2026) or a voice note.",
}
ASK_DISTRICT = {
    "mr": "📍 तुमचं गाव किंवा जिल्हा सांगा.",
    "hi": "📍 अपना गाँव या जिला बताएं।",
    "en": "📍 Tell me your village or district.",
}
ASK_IRRIGATION = {
    "mr": "💧 तुमच्याकडे पाण्याची सोय आहे का?\n\n1️⃣ होय\n2️⃣ नाही",
    "hi": "💧 क्या आपके पास सिंचाई की सुविधा है?\n\n1️⃣ हाँ\n2️⃣ नहीं",
    "en": "💧 Do you have irrigation?\n\n1️⃣ Yes\n2️⃣ No",
}
CROP_RETRY = {
    "mr": "कृपया 1, 2, 3 किंवा 4 पाठवा.\n",
    "hi": "कृपया 1, 2, 3 या 4 भेजें।\n",
    "en": "Please send 1, 2, 3 or 4.\n",
}
BAD_DATE = {
    "mr": "तारीख समजली नाही. उदा. 01-06-2026 अशी पाठवा.",
    "hi": "तारीख समझ नहीं आई। जैसे 01-06-2026 ऐसे भेजें।",
    "en": "I couldn't read the date. Send it like 01-06-2026.",
}
SOWN_LINE = {
    "mr": "✅ {crop}, {date} ला लावलं.\nपीक काढणी अंदाजे: *{harvest}* 🌾",
    "hi": "✅ {crop}, {date} को बोया।\nफसल कटाई अनुमानित: *{harvest}* 🌾",
    "en": "✅ {crop}, sown on {date}.\nExpected harvest: *{harvest}* 🌾",
}
NEXT_HDR = {
    "mr": "📅 *पुढील कामे:*",
    "hi": "📅 *अगले काम:*",
    "en": "📅 *Next tasks:*",
}
REMIND_NOTE = {
    "mr": "🔔 मी प्रत्येक कामाच्या आधी आठवण करेन.\n('पुढे' लिहा पुढची कामे पाहण्यासाठी.)",
    "hi": "🔔 मैं हर काम से पहले याद दिलाऊंगा।\n('आगे' लिखें अगले काम देखने के लिए।)",
    "en": "🔔 I'll remind you before each task.\n(Type 'next' to see upcoming tasks.)",
}
STAGE_LINE = {
    "mr": "🌱 सध्याची अवस्था: {stage} (दिवस {das})",
    "hi": "🌱 वर्तमान अवस्था: {stage} (दिन {das})",
    "en": "🌱 Current stage: {stage} (day {das})",
}
READY = {
    "mr": "🎉 तुमचं पीक तयार आहे! काढणी करा. (दिवस: {das})",
    "hi": "🎉 आपकी फसल तैयार है! कटाई करें। (दिन: {das})",
    "en": "🎉 Your crop is ready! Time to harvest. (day: {das})",
}
STOP_REPLY = {
    "mr": "🔕 ठीक आहे, मी आता आठवणी पाठवणार नाही. पुन्हा सुरू करण्यासाठी 'पुन्हा सुरू' लिहा.",
    "hi": "🔕 ठीक है, अब मैं रिमाइंडर नहीं भेजूंगा। फिर से शुरू करने के लिए 'resume' लिखें।",
    "en": "🔕 Okay, I won't send reminders anymore. Reply 'start reminders' to resume.",
}
RESUME_REPLY = {
    "mr": "🔔 छान! मी पुन्हा आठवणी पाठवेन.",
    "hi": "🔔 बढ़िया! मैं फिर से रिमाइंडर भेजूंगा।",
    "en": "🔔 Great! I'll send reminders again.",
}


def handle_message(num, body, media_url=None, media_type=None):
    """Public entry: route the message, then persist the session."""
    s = store.get(num)
    s["phone"] = num
    reply = _route(s, body, media_url, media_type)
    store.save(num, s)
    return reply


def _route(s, body, media_url=None, media_type=None):
    num = s["phone"]
    body = (body or "").strip()
    lang = s.get("lang", DEFAULT_LANG)

    # If the farmer sent a voice note, transcribe it first (needs ASR keys; if
    # none are set the bot just asks them to type — it never crashes).
    if media_url and media_type and "audio" in media_type:
        body = transcribe_voice(media_url) or body

    low = body.lower()

    # Opt-out (WhatsApp policy: farmers must be able to stop proactive messages).
    if low in ("stop", "unsubscribe", "बंद", "थांबा", "band", "रोको"):
        s["opted_out"] = True
        return L(STOP_REPLY, lang)
    if low in ("start reminders", "पुन्हा सुरू", "resume", "subscribe"):
        s["opted_out"] = False
        return L(RESUME_REPLY, lang)

    # Switch language anytime, without losing onboarding progress.
    if low in ("language", "lang", "भाषा", "भाषा बदला", "bhasha", "change language"):
        s["step"] = "lang"
        return ASK_LANG

    # Start / restart from scratch.
    if low in ("hi", "hello", "start", "नमस्कार", "namaskar", "restart"):
        s.clear()
        s.update({"phone": num, "step": "lang"})
        return ASK_LANG

    step = s["step"]

    # First contact -> ask language.
    if step in ("start", "lang") and not body:
        s["step"] = "lang"
        return ASK_LANG

    if step == "lang":
        chosen = LANG_BY_NUM.get(body) or LANG_BY_NAME.get(low)
        if not chosen:
            return ASK_LANG
        s["lang"] = chosen
        # If already onboarded, just confirm and show the plan in the new language.
        if s.get("crop") and s.get("sowing_date"):
            s["step"] = "done"
            return L(LANG_CHANGED, chosen) + "\n\n" + build_next_reply(s)
        s["step"] = "crop"
        return WELCOME[chosen]

    if step == "crop":
        crop = CROP_BY_NUM.get(body)
        if not crop:
            for key, names in sch.CROPS.items():
                if any(n.lower() in low for n in names.values()):
                    crop = key
                    break
        if not crop:
            return L(CROP_RETRY, lang) + WELCOME[lang]
        s["crop"] = crop
        s["step"] = "date"
        return L(ASK_DATE, lang)

    if step == "date":
        d = sch.parse_date(body)
        if not d:
            return L(BAD_DATE, lang)
        s["sowing_date"] = d.isoformat()
        s["step"] = "district"
        return L(ASK_DISTRICT, lang)

    if step == "district":
        s["district"] = body
        s["step"] = "irrigation"
        return L(ASK_IRRIGATION, lang)

    if step == "irrigation":
        s["irrigation"] = body in ("1", "होय", "हाँ", "yes", "haan")
        s["step"] = "done"
        return build_final_reply(s)

    # Already onboarded -> answer "what next".
    if step == "done":
        return build_next_reply(s)

    return ASK_LANG


def build_final_reply(s):
    lang = s.get("lang", DEFAULT_LANG)
    crop = s["crop"]
    sow = date.fromisoformat(s["sowing_date"])
    crop_name = sch.CROPS[crop][lang]
    harvest = sch.harvest_date(crop, sow)
    nxt = sch.next_tasks(crop, sow, n=3, lang=lang)

    task_lines = "\n".join(
        f"• *{t['date'].strftime('%d %b')}* — {t['text']}" for t in nxt
    )

    msg1 = L(SOWN_LINE, lang).format(
        crop=crop_name,
        date=sow.strftime("%d %b %Y"),
        harvest=harvest.strftime("%d %b %Y"),
    )
    msg2 = f"{L(NEXT_HDR, lang)}\n{task_lines}"

    alert = weather_alert(s.get("district", ""), lang)
    msg3 = (alert + "\n\n") if alert else ""
    msg3 += L(REMIND_NOTE, lang)

    # Optionally let Claude make it warmer/natural (falls back if no API key).
    return phrase_with_claude([msg1, msg2, msg3], lang)


def build_next_reply(s):
    lang = s.get("lang", DEFAULT_LANG)
    crop = s["crop"]
    sow = date.fromisoformat(s["sowing_date"])
    stage, das = sch.current_stage(crop, sow)
    nxt = sch.next_tasks(crop, sow, n=3, lang=lang)
    if not nxt:
        return L(READY, lang).format(das=das)
    task_lines = "\n".join(
        f"• *{t['date'].strftime('%d %b')}* — {t['text']}" for t in nxt
    )
    return f"{L(STAGE_LINE, lang).format(stage=stage, das=das)}\n\n{L(NEXT_HDR, lang)}\n{task_lines}"


@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    num = request.form.get("From", "")
    body = request.form.get("Body", "")
    media_url = request.form.get("MediaUrl0")
    media_type = request.form.get("MediaContentType0")

    reply = handle_message(num, body, media_url, media_type)

    resp = MessagingResponse()
    resp.message(reply)
    return str(resp)


@app.route("/chat", methods=["POST"])
def chat():
    """JSON endpoint for the browser demo (no Twilio needed)."""
    data = request.get_json(force=True)
    num = "web:" + data.get("session", "demo")
    reply = handle_message(num, data.get("body", ""))
    return {"reply": reply}


@app.route("/demo", methods=["GET"])
def demo():
    return DEMO_HTML


@app.route("/cron/reminders", methods=["GET", "POST"])
def cron_reminders():
    """Run the daily reminder job. Triggered by a free external scheduler
    (cron-job.org / GitHub Actions) since Render's cron service isn't free.
    Protected by a shared secret so randoms can't trigger sends."""
    import reminders
    secret = os.getenv("CRON_SECRET")
    if secret and request.args.get("key") != secret:
        return ("forbidden", 403)
    dry = request.args.get("dry") == "1"
    reminders.run(dry=dry)
    return {"ok": True, "dry": dry}


@app.route("/", methods=["GET"])
def health():
    return "Farmer WhatsApp bot is running ✅  →  open /demo for the browser chat"


DEMO_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>🌾 Farmer Assistant — Demo</title>
<style>
  body{margin:0;font-family:system-ui,Arial,sans-serif;background:#e5ddd5}
  #app{max-width:480px;margin:0 auto;height:100vh;display:flex;flex-direction:column;
       background:#efeae2;box-shadow:0 0 20px rgba(0,0,0,.15)}
  header{background:#075e54;color:#fff;padding:14px 16px;font-weight:600;display:flex;
         align-items:center;gap:10px}
  header .a{width:36px;height:36px;border-radius:50%;background:#25d366;display:flex;
            align-items:center;justify-content:center;font-size:18px}
  header select{margin-left:auto;background:#0b7a6d;color:#fff;border:none;border-radius:8px;
                padding:6px 8px;font-size:13px}
  #log{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:8px}
  .msg{max-width:78%;padding:8px 11px;border-radius:9px;white-space:pre-wrap;
       font-size:14.5px;line-height:1.35;box-shadow:0 1px 1px rgba(0,0,0,.08)}
  .bot{background:#fff;align-self:flex-start;border-top-left-radius:2px}
  .me{background:#d9fdd3;align-self:flex-end;border-top-right-radius:2px}
  .bot b,.me b{font-weight:700}
  footer{display:flex;gap:8px;padding:10px;background:#f0f0f0;align-items:center}
  input{flex:1;border:none;border-radius:20px;padding:11px 15px;font-size:15px;outline:none}
  button{border:none;background:#25d366;color:#fff;width:46px;height:46px;border-radius:50%;
         font-size:20px;cursor:pointer;flex:none}
  #mic.rec{background:#e53935;animation:pulse 1s infinite}
  @keyframes pulse{0%{opacity:1}50%{opacity:.5}100%{opacity:1}}
  .chips{display:flex;flex-wrap:wrap;gap:6px;padding:0 10px 10px;background:#f0f0f0}
  .chip{background:#fff;border:1px solid #ccc;border-radius:16px;padding:6px 12px;font-size:13px;
        cursor:pointer}
</style></head><body><div id="app">
  <header><div class="a">🌾</div> शेती मित्र · Farmer Assistant
    <select id="micLang" title="Voice language">
      <option value="mr-IN">🎤 मराठी</option>
      <option value="hi-IN">🎤 हिंदी</option>
      <option value="en-IN">🎤 English</option>
    </select>
  </header>
  <div id="log"></div>
  <div class="chips">
    <div class="chip" onclick="quick('hi')">hi</div>
    <div class="chip" onclick="quick('1')">1</div>
    <div class="chip" onclick="quick('01-06-2026')">01-06-2026</div>
    <div class="chip" onclick="quick('Akola')">Akola</div>
    <div class="chip" onclick="quick('next')">next</div>
  </div>
  <footer>
    <button id="mic" onclick="startVoice()" title="Speak">🎤</button>
    <input id="box" placeholder="Type or tap 🎤 to speak…" onkeydown="if(event.key==='Enter')send()">
    <button onclick="send()">➤</button>
  </footer>
</div>
<script>
const sess = Math.random().toString(36).slice(2);
const log = document.getElementById('log'), box = document.getElementById('box');
const mic = document.getElementById('mic');
function bubble(text, cls){
  const d = document.createElement('div');
  d.className = 'msg ' + cls;
  d.innerHTML = text.replace(/\\*(.+?)\\*/g,'<b>$1</b>').replace(/\\n/g,'<br>');
  log.appendChild(d); log.scrollTop = log.scrollHeight;
}
async function quick(t){ box.value = t; await send(); }
async function send(){
  const body = box.value.trim(); if(!body) return;
  bubble(body,'me'); box.value='';
  const r = await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({session:sess, body})});
  const j = await r.json(); bubble(j.reply,'bot');
}
// Voice input via the browser's built-in speech recognition (free, no API key).
function startVoice(){
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if(!SR){ alert('Voice input needs Google Chrome. Please type instead.'); return; }
  const rec = new SR();
  rec.lang = document.getElementById('micLang').value;
  rec.interimResults = false; rec.maxAlternatives = 1;
  mic.classList.add('rec'); mic.textContent = '🔴';
  rec.onresult = e => { box.value = e.results[0][0].transcript; send(); };
  rec.onerror = e => { alert('Voice error: ' + e.error + '. In Brave, enable Web Speech, or use Chrome.'); };
  rec.onend = () => { mic.classList.remove('rec'); mic.textContent = '🎤'; };
  rec.start();
}
bubble('👋 Send "hi" to start (or tap a chip). Tap 🎤 to speak.','bot');
</script></body></html>
"""


if __name__ == "__main__":
    # Local dev only. In production gunicorn serves `app` (see Procfile).
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=debug)
