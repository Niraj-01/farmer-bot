"""
WhatsApp farming-assistant bot (Twilio Sandbox).
Flow:  crop -> sowing date -> district -> irrigation -> full dated schedule.
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

# Sessions are persisted in SQLite (store.py) so the reminder cron can
# reach farmers across restarts.

LANG = "mr"  # default demo language: Marathi. Switch to "hi" or "en" as needed.

WELCOME = {
    "mr": "नमस्कार! 🌾 मी तुमचा शेती मित्र. तुम्ही कोणतं पीक लावलं आहे?\n\n1️⃣ कापूस\n2️⃣ सोयाबीन\n3️⃣ गहू\n4️⃣ तूर\n\n(नंबर पाठवा किंवा बोला)",
    "hi": "नमस्ते! 🌾 मैं आपका खेती मित्र हूँ। आपने कौन सी फसल लगाई है?\n\n1️⃣ कपास\n2️⃣ सोयाबीन\n3️⃣ गेहूं\n4️⃣ तुअर",
    "en": "Hello! 🌾 I am your farming assistant. Which crop did you sow?\n\n1️⃣ Cotton\n2️⃣ Soybean\n3️⃣ Wheat\n4️⃣ Tur",
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

    # If the farmer sent a voice note, transcribe it first.
    if media_url and media_type and "audio" in media_type:
        body = transcribe_voice(media_url) or body

    step = s["step"]

    # Allow restart anytime
    if body.lower() in ("hi", "hello", "start", "नमस्कार", "namaskar", "restart"):
        s.clear()
        s.update({"phone": num, "step": "crop"})
        return WELCOME[LANG]

    if step == "start":
        s["step"] = "crop"
        return WELCOME[LANG]

    if step == "crop":
        crop = CROP_BY_NUM.get(body)
        if not crop:
            # try matching crop name from text/voice
            for key, names in sch.CROPS.items():
                if any(n.lower() in body.lower() for n in names.values()):
                    crop = key
                    break
        if not crop:
            return "कृपया 1, 2, 3 किंवा 4 पाठवा.\n" + WELCOME[LANG]
        s["crop"] = crop
        s["step"] = "date"
        return ASK_DATE[LANG]

    if step == "date":
        d = sch.parse_date(body)
        if not d:
            return "तारीख समजली नाही. उदा. 01-06-2026 अशी पाठवा."
        s["sowing_date"] = d.isoformat()
        s["step"] = "district"
        return ASK_DISTRICT[LANG]

    if step == "district":
        s["district"] = body
        s["step"] = "irrigation"
        return ASK_IRRIGATION[LANG]

    if step == "irrigation":
        s["irrigation"] = body in ("1", "होय", "हाँ", "yes", "haan")
        s["step"] = "done"
        return build_final_reply(s)

    # Already onboarded -> answer "what next"
    if step == "done":
        return build_next_reply(s)

    return WELCOME[LANG]


def build_final_reply(s):
    crop = s["crop"]
    sow = date.fromisoformat(s["sowing_date"])
    crop_name = sch.CROPS[crop][LANG]
    harvest = sch.harvest_date(crop, sow)
    nxt = sch.next_tasks(crop, sow, n=3, lang=LANG)

    lines = [t for t in nxt]
    task_lines = "\n".join(
        f"• *{t['date'].strftime('%d %b')}* — {t['text']}" for t in lines
    )

    msg1 = f"✅ {crop_name}, {sow.strftime('%d %b %Y')} ला लावलं.\nपीक काढणी अंदाजे: *{harvest.strftime('%d %b %Y')}* 🌾"
    msg2 = f"📅 *पुढील कामे:*\n{task_lines}"

    alert = weather_alert(s.get("district", ""))
    msg3 = (alert + "\n\n") if alert else ""
    msg3 += "🔔 मी प्रत्येक कामाच्या आधी तुम्हाला आठवण करेन.\n('पुढे' लिहा पुढची कामे पाहण्यासाठी.)"

    # Optionally let Claude make it warmer/natural (falls back if no API key)
    final = phrase_with_claude([msg1, msg2, msg3], LANG)
    return final


def build_next_reply(s):
    crop = s["crop"]
    sow = date.fromisoformat(s["sowing_date"])
    stage, das = sch.current_stage(crop, sow)
    nxt = sch.next_tasks(crop, sow, n=3, lang=LANG)
    if not nxt:
        return f"🎉 तुमचं पीक तयार आहे! काढणी करा. (दिवस: {das})"
    task_lines = "\n".join(
        f"• *{t['date'].strftime('%d %b')}* — {t['text']}" for t in nxt
    )
    return f"🌱 सध्याची अवस्था: {stage} (दिवस {das})\n\n📅 पुढील कामे:\n{task_lines}"


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
  #log{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:8px;
       background-image:url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22/>')}
  .msg{max-width:78%;padding:8px 11px;border-radius:9px;white-space:pre-wrap;
       font-size:14.5px;line-height:1.35;box-shadow:0 1px 1px rgba(0,0,0,.08)}
  .bot{background:#fff;align-self:flex-start;border-top-left-radius:2px}
  .me{background:#d9fdd3;align-self:flex-end;border-top-right-radius:2px}
  .bot b,.me b{font-weight:700}
  footer{display:flex;gap:8px;padding:10px;background:#f0f0f0}
  input{flex:1;border:none;border-radius:20px;padding:11px 15px;font-size:15px;outline:none}
  button{border:none;background:#25d366;color:#fff;width:46px;height:46px;border-radius:50%;
         font-size:20px;cursor:pointer}
  .chips{display:flex;flex-wrap:wrap;gap:6px;padding:0 10px 10px;background:#f0f0f0}
  .chip{background:#fff;border:1px solid #ccc;border-radius:16px;padding:6px 12px;font-size:13px;
        cursor:pointer}
</style></head><body><div id="app">
  <header><div class="a">🌾</div> शेती मित्र · Farmer Assistant</header>
  <div id="log"></div>
  <div class="chips">
    <div class="chip" onclick="quick('hi')">hi</div>
    <div class="chip" onclick="quick('1')">1 कापूस</div>
    <div class="chip" onclick="quick('01-06-2026')">01-06-2026</div>
    <div class="chip" onclick="quick('Akola')">Akola</div>
    <div class="chip" onclick="quick('पुढे')">पुढे</div>
  </div>
  <footer>
    <input id="box" placeholder="Type a message…" onkeydown="if(event.key==='Enter')send()">
    <button onclick="send()">➤</button>
  </footer>
</div>
<script>
const sess = Math.random().toString(36).slice(2);
const log = document.getElementById('log'), box = document.getElementById('box');
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
bubble('👋 Send "hi" to start (or tap a chip below).','bot');
</script></body></html>
"""


if __name__ == "__main__":
    # Local dev only. In production gunicorn serves `app` (see Procfile).
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=debug)
