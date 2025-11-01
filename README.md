# Serenity Bot 🧘 — Youth Mental Wellness (Free Stack)

A free-to-run Streamlit app that uses **Gemini 2.5 Flash**, **Firebase (Auth + Firestore)**, and includes:

- MoodTracker + Journal (daily, charts)
- Affirmations (based on mood history)
- Breathing Coach (HTML canvas animation)
- Anonymous "Letter to Yourself" (returns in-app after 7 days)
- Crisis Detection (text-only, helplines for India)
- Audio & Text inputs
- Multi-user via Firebase Auth (REST)
- Adaptive conversation styles
- Insights dashboard

## Quickstart

1. Create a Google AI Studio key (free): https://aistudio.google.com/
2. Create a Firebase project (free tier). Enable Authentication (Email/Password or Anonymous) and Firestore.
3. Download a **Service Account JSON** from Firebase Console (Project Settings → Service Accounts).
4. Copy `.env.example` to `.env` and fill values for:
   - `GOOGLE_API_KEY`
   - `FIREBASE_WEB_API_KEY`
   - `FIREBASE_SERVICE_ACCOUNT_JSON` (paste the JSON as one line)
5. Install packages:

```bash
pip install -r requirements.txt
```

6. Run the app:

```bash
streamlit run app.py
```

## Free Hosting

- **Streamlit Community Cloud** (free): push this folder to a public GitHub repo and deploy.
- Or **Hugging Face Spaces** (Streamlit template).

## Notes

- Email reminders require additional setup (e.g., Gmail API or Cloud Functions). This app shows letters in-app once the scheduled date passes.
- All features run under free tiers; monitor quotas.


# 🧘 Serenity Bot — Mental Wellness Assistant (Streamlit + Firebase + Gemini)

Serenity Bot is an AI-driven wellness companion built using **Streamlit**, **Google Gemini API**, and **Firebase**.  
It helps users track moods, write journals, play focus-building games, and gain insights into their emotional health — all in a free, privacy-friendly stack.

---

## 🏗️ System Overview

### 🔹 Architecture

            ┌────────────────────────────┐
            │        Frontend UI          │
            │ (Streamlit Web Interface)   │
            └─────────────┬───────────────┘
                          │
                          │ REST + Secrets (local/cloud)
                          ▼
            ┌────────────────────────────┐
            │      Application Layer      │
            │  (app.py, utils/*.py)       │
            │------------------------------│
            │  • Authentication (Firebase) │
            │  • Chat + Gemini API Calls   │
            │  • Mood Tracking & Insights  │
            │  • Mini Games & Doodle Tool  │
            │  • Breathing Coach & Journal │
            └─────────────┬───────────────┘
                          │
                          ▼
            ┌────────────────────────────┐
            │        Firebase Layer       │
            │  (Firestore + Auth + Rules) │
            │------------------------------│
            │  • User data, moods, letters│
            │  • Secure access (server key)│
            └─────────────┬───────────────┘
                          │
                          ▼
            ┌────────────────────────────┐
            │     Google Gemini 2.5 API   │
            │     (AI text generation)    │
            └────────────────────────────┘


---

## ⚙️ Tech Stack

| Layer | Technology | Description |
|-------|-------------|-------------|
| **Frontend** | Streamlit | Interactive UI for journaling, charts, and games |
| **Backend** | Firebase Firestore + Auth | Secure data storage + multi-user management |
| **AI Engine** | Google Gemini 2.5 Flash | Contextual conversation, affirmations, crisis detection |
| **Analytics** | Plotly + Pandas | Mood insights, weekly averages, streaks |
| **Extras** | streamlit-drawable-canvas, streamlit-mic-recorder, gTTS | Doodling, voice input, text-to-speech |
| **Lang/Runtime** | Python 3.10+ | All features implemented in Python |

---

## 🧠 Key Functional Modules

| Module | Purpose |
|---------|----------|
| `app.py` | Main Streamlit entry; manages tabs, routing, session, UI state |
| `utils/db.py` | Firestore CRUD (moods, letters, memories, schedules) |
| `utils/auth.py` | Firebase REST authentication |
| `utils/insights.py` | Mood analytics, KPI computation, visualizations |
| `utils/games.py` | Emoji Memory Match, Doodle Canvas |
| `utils/helpers.py` | Helper functions for formatting, user state, etc. |

---

## ✨ Features

- 🧠 **AI Chat** — mood-aware responses powered by Gemini
- 🗓️ **Mood Tracker** — 14-day logs with charts + export
- 🌈 **Affirmations** — personalized by your emotional history
- 💌 **Letter to Yourself** — scheduled reflections after 7 days
- 📊 **Insights Dashboard** — weekly average mood, streaks, trends
- 🧩 **Mini Games** — Emoji Memory Match & Doodle Canvas (sparkle effect)
- 🌬️ **Breathing Coach** — guided breathing animation (canvas-based)
- 🗂️ **Memory + Schedule** — persistent memory system for personal context
- 🎙️ **Voice Input** — optional audio-based logging (mic recorder)
- 🆘 **Crisis Detection** — detects sensitive phrases and shows helplines (India)
- 🔐 **Multi-user Login** — Firebase Auth (anonymous or email/password)

---

## 🚀 Quickstart (Local Development)

### 1️⃣ Prerequisites
- Python 3.10+
- Google AI Studio API key → [https://aistudio.google.com/](https://aistudio.google.com/)
- Firebase project (Firestore + Authentication enabled)

### 2️⃣ Get Credentials
- In Firebase Console → **Project Settings → Service Accounts**
- Click **“Generate new private key”** → download the JSON file.

### 3️⃣ Environment Setup

Create `.env` in your project root:

GOOGLE_API_KEY=your_gemini_api_key
FIREBASE_WEB_API_KEY=your_firebase_web_api_key
FIREBASE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"your_project",...}


### 4️⃣ Install Dependencies
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt



streamlit run app.py

🧱 Required Firestore Indexes

Create the following Composite Indexes (Firestore Console → Indexes → “Add Index”):

| Field   | Order     |
| ------- | --------- |
| user_id | Ascending |
| date    | Ascending |

| Field      | Order     |
| ---------- | --------- |
| user_id    | Ascending |
| delivered  | Ascending |
| deliver_on | Ascending |

| Field        | Order     |
| ------------ | --------- |
| user_id      | Ascending |
| created_date | Ascending |


💡 If you see “The query requires an index” in logs, click the link — Firebase pre-fills everything.

🧩 Project Structure
serenity_bot/
├── app.py
├── utils/
│   ├── auth.py
│   ├── db.py
│   ├── helpers.py
│   ├── insights.py
│   ├── games.py
├── .streamlit/
│   └── secrets.toml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md

## ☁️ Deployment (Streamlit Cloud)
Step 1: Push to GitHub
git init
git add .
git commit -m "Initial commit: Serenity Bot"
git branch -M main
git remote add origin https://github.com/<username>/serenity-bot.git
git push -u origin main

Step 2: Deploy

Visit https://share.streamlit.io

Click “New App” → choose your repo → main branch → file: app.py

Step 3: Add Secrets

Go to App → Settings → Secrets, and paste:

FIREBASE_SERVICE_ACCOUNT_JSON = """
{ ...full JSON content from Firebase... }
"""
FIREBASE_API_KEY = "your_firebase_web_api_key"
GOOGLE_API_KEY = "your_gemini_api_key"

Step 4: Run

Streamlit Cloud will automatically install dependencies from requirements.txt and start the app.
If index errors appear, click the “Create index” link → wait until Status = Ready → reload.

## 🔒 Security Notes

Never commit .env or service account JSON. Use Streamlit Secrets.

This app uses Firebase Admin SDK — all database writes are server-side.

Enable Firestore Rules if you later expose a client-side API.

Store sensitive data like memories & journals only under authenticated users.

## 📊 Insights Module Overview

Calculates average mood (1–5 scale)

Displays weekly mood chart via Plotly

Tracks streaks (continuous daily entries)

Identifies most frequent mood

Auto-updates metrics every 30 days

## 🧩 Mini Games (Focus & Calm Tools)
Game	Description
🎴 Emoji Memory Match	Cognitive focus training game; tracks moves and time
🎨 Doodle Canvas	Free-draw board with sparkle overlay; saves as PNG
🙏 Gratitude Picker	Select 3 gratitude points; logs as positive activity
🧘 Breathing Coach

Implements Box Breathing with a canvas animation:

4s Inhale → 4s Hold → 4s Exhale → 4s Hold

Optional soft background music loop

Visual ring expands/contracts for calm practice

##🧠 AI Logic (Gemini)

Uses Google Gemini 2.5 Flash (via REST)

Context-fed with user’s last mood + memory

Crisis keyword detection → mental health helpline

Adaptive responses: calm, supportive, or cheerful tone

##🗂️ Data Model
Collection	Fields	Description
users	user_id, email	Auth & profile info
moods	mood, note, date, user_id	Daily tracking
letters	title, message, deliver_on, delivered	Delayed reflections
memories	user_id, text, created_date	Persistent memory store
schedules	user_id, activity, time	Time-based memory checks

##🧠 Future Enhancements

Push notifications for letters & reminders

Emotion detection from voice/audio

Expanded crisis support by region

Personalized affirmations via fine-tuned models

##🙏 Credits & Resources


Streamlit: https://streamlit.io
 — Framework for building interactive web apps in Python

Firebase: https://firebase.google.com
 — Backend-as-a-service (Auth, Firestore, Hosting, etc.)

Google AI Studio (Gemini): https://aistudio.google.com
 — Google’s platform for Gemini API access and experimentation

Plotly: https://plotly.com/python/

 — Data visualization library for Python (interactive charts)

streamlit-mic-recorder: https://pypi.org/project/streamlit-mic-recorder/
 — Microphone recorder component for Streamlit apps

streamlit-drawable-canvas: https://github.com/andfanilo/streamlit-drawable-canvas
 — Interactive drawing canvas for Streamlit

gTTS (Google Text-to-Speech): https://pypi.org/project/gTTS/
 — Python library for text-to-speech synthesis using Google Translate API

##📜 License

MIT License © 2025 Serenity Bot — Developed by Tanuja Dattatraya Ratan
“Serenity begins when you start listening to your own silence.” — Serenity Bot (2025)


---

### ✅ What this version gives you:
- Complete **technical + architectural explanation**
- **Setup + deployment instructions** for both local & Streamlit Cloud
- **Firestore index definitions**
- Professional tone (for GitHub/portfolio)
- Keeps your **Gemini, Firebase, and Streamlit stack details**
