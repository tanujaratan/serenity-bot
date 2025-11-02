# utils/db.py
import os, json, datetime
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import FieldFilter

try:
    import streamlit as st
except Exception:
    st = None  # allows local scripts/tests without Streamlit

_app = None


def _init():
    """Initialize Firebase exactly once."""
    global _app
    if _app is not None:
        return
    if firebase_admin._apps:
        _app = firebase_admin.get_app()
        return

    cred = None

    # 1️⃣ Prefer Streamlit Secrets TOML table
    if st is not None and hasattr(st, "secrets") and "FIREBASE_SERVICE_ACCOUNT" in st.secrets:
        info = dict(st.secrets["FIREBASE_SERVICE_ACCOUNT"])
        cred = credentials.Certificate(info)

    # 2️⃣ Fallback: JSON string in environment (for local dev / Streamlit Cloud)
    elif os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"):
        svc_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON").strip()

        # Fix common TOML/triple-quote issues
        if svc_json.startswith('"""') and svc_json.endswith('"""'):
            svc_json = svc_json[3:-3].strip()

        # Replace escaped newlines with real newlines
        svc_json = svc_json.replace('\\n', '\n')

        try:
            info = json.loads(svc_json)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                "FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON. "
                "Paste the exact JSON (no extra quotes)."
            ) from e

        cred = credentials.Certificate(info)

    else:
        raise RuntimeError(
            "Missing Firebase credentials. Provide [FIREBASE_SERVICE_ACCOUNT] in Streamlit secrets, "
            "or set FIREBASE_SERVICE_ACCOUNT_JSON in environment."
        )

    _app = firebase_admin.initialize_app(cred)


def _client():
    _init()
    return firestore.client()


# -----------------------------
# Public API
# -----------------------------
def log_mood(user_id: str, mood: str, note: str, reflection: str):
    db = _client()
    return db.collection("moods").add({
        "user_id": user_id,
        "mood": mood,
        "note": note,
        "reflection": reflection,
        "date": datetime.date.today().isoformat(),
        "ts": firestore.SERVER_TIMESTAMP,
    })


def list_recent_moods(user_id: str, days: int = 14):
    db = _client()
    since = datetime.date.today() - datetime.timedelta(days=days)
    q = (db.collection("moods")
           .where(filter=FieldFilter("user_id", "==", user_id))
           .where(filter=FieldFilter("date", ">=", since.isoformat()))
           .order_by("date"))
    return [{**d.to_dict(), "id": d.id} for d in q.stream()]


def store_letter(user_id: str, content: str, deliver_on: str):
    db = _client()
    return db.collection("letters").add({
        "user_id": user_id,
        "content": content,
        "deliver_on": deliver_on,
        "delivered": False,
        "ts": firestore.SERVER_TIMESTAMP,
    })


def due_letters(user_id: str):
    db = _client()
    today = datetime.date.today().isoformat()
    q = (db.collection("letters")
           .where(filter=FieldFilter("user_id", "==", user_id))
           .where(filter=FieldFilter("delivered", "==", False))
           .where(filter=FieldFilter("deliver_on", "<=", today)))
    return [{**d.to_dict(), "id": d.id} for d in q.stream()]


def mark_letter_delivered(doc_id: str):
    db = _client()
    db.collection("letters").document(doc_id).update({"delivered": True})


def _today_iso():
    return datetime.date.today().isoformat()


def update_daily_report(user_id: str):
    db = _client()
    today = _today_iso()
    moods_snap = (db.collection("moods")
                    .where(filter=FieldFilter("user_id", "==", user_id))
                    .where(filter=FieldFilter("date", "==", today))
                 ).stream()
    moods = [d.to_dict() for d in moods_snap]

    mood_map = {
        "😊 Happy": 5, "🎉 Excited": 5, "😌 Calm": 5,
        "🙂 Okay": 4, "😟 Anxious": 2, "😢 Sad": 1,
        "😠 Angry": 1, "😴 Tired": 2, "🤒 Unwell": 1,
        "⭐ Good Deed": 5, "🙏 Gratitude": 5,
    }

    scores = [mood_map.get(m.get("mood", ""), 3) for m in moods]
    avg = (sum(scores) / len(scores)) if scores else None
    good_deeds = [m for m in moods if m.get("mood") in ["⭐ Good Deed", "🙏 Gratitude"]]

    doc = {
        "user_id": user_id,
        "date": today,
        "count_entries": len(moods),
        "avg_score": avg,
        "good_deeds": len(good_deeds),
        "notes": [m.get("note", "") for m in moods if m.get("note")],
        "ts": firestore.SERVER_TIMESTAMP,
    }
    db.collection("daily_reports").document(f"{user_id}_{today}").set(doc, merge=True)


def add_memory(user_id: str, key: str, value: str, tags=None, importance=3, expires_on=None):
    db = _client()
    doc = {
        "user_id": user_id,
        "key": key.strip(),
        "value": value.strip(),
        "tags": tags or [],
        "importance": int(importance),
        "created_date": datetime.date.today().isoformat(),
        "expires_on": expires_on,
        "ts": firestore.SERVER_TIMESTAMP,
    }
    return db.collection("memories").add(doc)


def list_memories(user_id: str, limit=100):
    db = _client()
    q = db.collection("memories").where(filter=FieldFilter("user_id", "==", user_id))
    rows = [{**d.to_dict(), "id": d.id} for d in q.stream()]

    def _key(rec):
        cd = rec.get("created_date") or ""
        ts = rec.get("ts")
        return (cd, str(ts))

    rows.sort(key=_key)
    return rows[:limit]


def add_schedule_item(user_id, title, days, start_time, end_time,
                      location="", notes="", priority=3, travel_mins=0):
    db = _client()
    doc = {
        "user_id": user_id,
        "title": title.strip(),
        "days": [d.strip() for d in days],
        "start_time": start_time.strip(),
        "end_time": end_time.strip(),
        "location": location.strip(),
        "notes": notes.strip(),
        "priority": int(priority),
        "travel_mins": int(travel_mins),
        "ts": firestore.SERVER_TIMESTAMP,
    }
    return db.collection("schedules").add(doc)


def list_schedule(user_id):
    db = _client()
    q = db.collection("schedules").where(filter=FieldFilter("user_id", "==", user_id))
    out = []
    for d in q.stream():
        rec = d.to_dict()
        rec["id"] = d.id
        rec.setdefault("priority", 3)
        rec.setdefault("travel_mins", 0)
        out.append(rec)
    return out
