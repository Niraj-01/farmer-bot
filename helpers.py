"""
External integrations: voice transcription, weather, Claude phrasing.
All three DEGRADE GRACEFULLY — if an API key is missing, the bot still works
with sensible fallbacks so your demo never crashes.
"""
import os
import requests

# ---------- 1. Voice note -> text ----------
def transcribe_voice(media_url):
    """
    Download the WhatsApp voice note and transcribe it.
    Recommended for Indian languages: AI4Bharat Bhashini (free, govt) or Whisper.
    Demo fallback: returns None so the bot asks the user to type instead.
    """
    # Prefer Bhashini (free, Indian govt, best for Marathi/Hindi) if configured.
    if os.getenv("BHASHINI_API_KEY"):
        text = transcribe_bhashini(media_url)
        if text:
            return text
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        # Twilio media needs basic auth (your Twilio SID/token)
        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        audio = requests.get(media_url, auth=(sid, token), timeout=20)
        files = {"file": ("voice.ogg", audio.content, "audio/ogg")}
        data = {"model": "whisper-1"}  # auto-detects Marathi/Hindi
        r = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files=files, data=data, timeout=60,
        )
        return r.json().get("text")
    except Exception as e:
        print("transcribe error:", e)
        return None


def transcribe_bhashini(media_url, source_lang="mr"):
    """
    Transcribe using Bhashini (bhashini.gov.in) ASR — free Indian govt service,
    strongest for Marathi/Hindi. You need to register at bhashini.gov.in and get:
      BHASHINI_API_KEY, BHASHINI_USER_ID, BHASHINI_INFERENCE_URL, BHASHINI_ASR_SERVICE_ID
    Flow: download audio -> base64 -> POST to the ASR pipeline.
    Returns transcript text, or None on any failure (so callers fall back).
    """
    import base64
    try:
        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        audio = requests.get(media_url, auth=(sid, token), timeout=20).content
        audio_b64 = base64.b64encode(audio).decode()

        payload = {
            "pipelineTasks": [{
                "taskType": "asr",
                "config": {
                    "language": {"sourceLanguage": source_lang},
                    "serviceId": os.getenv("BHASHINI_ASR_SERVICE_ID"),
                    "audioFormat": "ogg",
                    "samplingRate": 16000,
                },
            }],
            "inputData": {"audio": [{"audioContent": audio_b64}]},
        }
        r = requests.post(
            os.getenv("BHASHINI_INFERENCE_URL"),
            headers={
                "Authorization": os.getenv("BHASHINI_API_KEY"),
                "userID": os.getenv("BHASHINI_USER_ID", ""),
                "Content-Type": "application/json",
            },
            json=payload, timeout=60,
        )
        return r.json()["pipelineResponse"][0]["output"][0]["source"]
    except Exception as e:
        print("bhashini error:", e)
        return None


# ---------- 2. Weather alert ----------
RAIN_ALERT = {
    "mr": "⚠️ पुढील २४ तासात पाऊस आहे ☔ — फवारणी पुढे ढकला.",
    "hi": "⚠️ अगले 24 घंटे में बारिश है ☔ — छिड़काव टालें।",
    "en": "⚠️ Rain expected in next 24h ☔ — delay spraying.",
}


def weather_alert(district, lang="mr"):
    """
    Check forecast for the district. If rain expected, return a spray-delay alert
    in the farmer's language. Demo fallback: if no API key, return a canned alert
    so the 'smart' moment still works.
    """
    alert_text = RAIN_ALERT.get(lang, RAIN_ALERT["mr"])
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key or not district:
        # Canned demo alert — comment out for a fully live demo.
        return alert_text
    try:
        geo = requests.get(
            "http://api.openweathermap.org/geo/1.0/direct",
            params={"q": f"{district},IN", "limit": 1, "appid": api_key},
            timeout=10,
        ).json()
        if not geo:
            return ""
        lat, lon = geo[0]["lat"], geo[0]["lon"]
        fc = requests.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
            timeout=10,
        ).json()
        # Look at next ~24h (8 x 3-hour slots)
        rain_soon = any(
            "rain" in (slot.get("weather", [{}])[0].get("main", "").lower())
            for slot in fc.get("list", [])[:8]
        )
        if rain_soon:
            return alert_text
        return ""
    except Exception as e:
        print("weather error:", e)
        return ""


# ---------- 3. Claude — natural-language phrasing ----------
def phrase_with_claude(messages, lang="mr"):
    """
    Optionally rewrite the schedule messages in warm, simple farmer-friendly
    language. Falls back to joining the raw messages if no API key.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    joined = "\n\n".join(messages)
    if not api_key:
        return joined
    try:
        lang_name = {"mr": "Marathi", "hi": "Hindi", "en": "English"}[lang]
        prompt = (
            f"You are a friendly village agriculture assistant talking to a farmer "
            f"on WhatsApp in {lang_name}. Rewrite the following into one warm, very "
            f"simple message a non-literate farmer can understand. Keep all dates, "
            f"quantities and emojis. Do not add new farming advice.\n\n{joined}"
        )
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-opus-4-8",
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        return r.json()["content"][0]["text"]
    except Exception as e:
        print("claude error:", e)
        return joined
