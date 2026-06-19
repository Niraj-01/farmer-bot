# 🌾 Pitch Deck Outline — Farmer WhatsApp Assistant

A slide-by-slide outline for the client pitch. ~10 slides, 8–10 min.

---

### Slide 1 — Title
**Your AI Farming Assistant — on WhatsApp, by voice, in Marathi.**
One line: *"Tells every farmer exactly what to do, and when — before they ask."*

### Slide 2 — The problem
- Farmers miss the right window for irrigation, fertilizer, spraying → lower yield.
- Most are not literate and don't own smartphones/apps — but **everyone has WhatsApp**.
- A chatbot waits to be asked. Farmers don't know *what* to ask.

### Slide 3 — Why the old chatbot idea fails
- Reactive Q&A = farmer must already know the question.
- No memory of *their* crop, *their* dates.
- Text-only excludes non-readers.
→ We flip it: **proactive, dated, voice-first, personalized.**

### Slide 4 — The solution (one screen)
Farmer answers **4 simple questions** (crop, sowing date, district, irrigation) →
gets a **personalized dated calendar** + **automatic reminders before each task** +
**weather-based alerts**. All on WhatsApp. Voice notes supported.

### Slide 5 — Live demo (the heart of the pitch)
Show the real WhatsApp chat:
1. "hi" → crop list
2. Send a **voice note**: *"मी १ जून ला कापूस लावला"*
3. District + irrigation
4. 💥 Instant calendar: harvest date + next 3 dated tasks + rain alert
5. Show a **reminder** arriving on its own.
**Call out 3 wow moments:** understood voice • exact dates not generic tips • plan changed for weather.

### Slide 6 — How it works (simple diagram)
`Voice/Text → Bhashini speech-to-text → Crop knowledge table + sowing date math
→ Weather API → WhatsApp reply + daily reminder cron`
Key message: **the "brain" is verified agronomy data, not a guessing AI.**

### Slide 7 — Data & trust
- Schedules sourced from **agricultural-university Package of Practices** & KVK.
- **Validated by agronomists** (ask client to provide one).
- Localized to crop + region + irrigation.
- Languages: Marathi / Hindi / English via **Bhashini** (Indian govt, free).

### Slide 8 — What's built today (MVP)
- ✅ WhatsApp bot, 4-question flow
- ✅ 4 crops (cotton, soybean, wheat, tur), 50+ dated tasks
- ✅ Voice-note transcription
- ✅ Weather alerts
- ✅ **Proactive daily reminders**
Running now on Twilio + a live number.

### Slide 9 — Roadmap
- **Phase 2:** Disease detection from a leaf photo; market prices (e-NAM); govt schemes.
- **Phase 3:** Yield prediction; per-farmer personalization from feedback; more crops/regions.
- **Scale:** Move to official WhatsApp Business API + cooperatives/KVK partnerships.

### Slide 10 — Impact & ask
- Impact: fewer missed windows → higher yield, less input waste.
- Metrics: # farmers onboarded, task-completion rate, yield delta in pilot.
- **The ask:** pick 1 district + 3 crops for a pilot; provide an agronomist to validate data; target N farmers in 60 days.

---

## One-liners to keep saying
- "A chatbot answers. This *advises* — on time, every time."
- "No app to download. No reading required. Just WhatsApp and your voice."
- "The intelligence is verified agronomy, delivered personally."
