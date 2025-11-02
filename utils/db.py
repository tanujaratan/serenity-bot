# utils/db.py
import os, json, base64, datetime
from firebase_admin import credentials, firestore, initialize_app
from google.cloud.firestore_v1 import FieldFilter

# Keep Firebase initialized once
_app = None

def _init():
    """Initialize Firebase using base64-encoded service account."""
    global _app
    if _app is not None:
        return
    # Reuse if already initialized elsewhere
    import firebase_admin
    if firebase_admin._apps:
        _app = firebase_admin.get_app()
        return

    # Prefer base64 service account (safer)
    b64 = os.environ.get("FIREBASE_SERVICE_ACCOUNT_B64", "").strip()
    if not b64:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_B64 missing in environment or secrets.")

    try:
        svc_json = base64.b64decode(b64).decode("utf-8")
        cred_dict = json.loads(svc_json)
    except Exception as e:
        raise RuntimeError("Failed to decode Firebase service account. Ensure it's base64 of the full JSON file.") from e

    # Sanity check
    pk = cred_dict.get("private_key", "")
    if not (pk.startswith("-----BEGIN PRIVATE KEY-----") and pk.strip().endswith("-----END PRIVATE KEY-----")):
        raise RuntimeError("Invalid private key block in service account JSON. Recreate base64 correctly.")

    cred = credentials.Certificate(cred_dict)
    _app = initialize_app(cred)


def _client():
    """Return Firestore client (initialize if needed)."""
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
        "date": datetime.date.today().isoformat(),  # YYYY-MM-DD (string)
        "ts": firestore.SERVER_TIMESTAMP,           # Firestore Timestamp
    })

def list_recent_moods(user_id: str, days: int = 14):
    """Last `days` moods for user, ordered by date (string YYYY-MM-DD)."""
    db = _client()
    since = datetime.date.today() - datetime.timedelta(days=days)
    q = (db.collection("moods")
           .where(filter=FieldFilter("user_id", "==", user_id))
           .where(filter=FieldFilter("date", ">=", since.isoformat()))
           .order_by("date"))
    return [{**d.to_dict(), "id": d.id} for d in q.stream()]

def store_letter(user_id: str, content: str, deliver_on: str):
    """Store a letter to be shown on/after deliver_on (YYYY-MM-DD)."""
    db = _client()
    return db.collection("letters").add({
        "user_id": user_id,
        "content": content,
        "deliver_on": deliver_on,
        "delivered": False,
        "ts": firestore.SERVER_TIMESTAMP,
    })

def due_letters(user_id: str):
    """Letters due today or earlier that are not delivered."""
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

# -----------------------------
# Daily report aggregation
# -----------------------------

def _today_iso():
    return datetime.date.today().isoformat()

def update_daily_report(user_id: str):
    """
    Aggregate today's moods/notes into a single daily_reports doc.
    """
    db = _client()
    today = _today_iso()

    # Pull today's moods/notes for this user
    moods_snap = (db.collection("moods")
                    .where(filter=FieldFilter("user_id", "==", user_id))
                    .where(filter=FieldFilter("date", "==", today))
                 ).stream()
    moods = [d.to_dict() for d in moods_snap]

    # Include new positives so averages are correct
    mood_map = {
        "😊 Happy": 5,
        "🎉 Excited": 5,
        "😌 Calm": 5,
        "🙂 Okay": 4,
        "😟 Anxious": 2,
        "😢 Sad": 1,
        "😠 Angry": 1,
        "😴 Tired": 2,
        "🤒 Unwell": 1,
        "⭐ Good Deed": 5,
        "🙏 Gratitude": 5,
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

# -----------------------------
# Personal memory & weekly schedule
# -----------------------------
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

    # Sort by created_date (YYYY-MM-DD string) and then by ts for stability
    def _key(rec):
        cd = rec.get("created_date") or ""
        ts = rec.get("ts")  # Firestore Timestamp or None
        return (cd, str(ts))

    rows.sort(key=_key)  # ascending = oldest first
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
