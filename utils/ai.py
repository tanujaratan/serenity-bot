
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL = "gemini-2.5-flash"

_system_persona_base = """You are Serenity, a youth mental wellness companion.
- Be empathetic, clear, and human. Sound like a caring close friend; warm, a little playful, never clinical.
- Offer practical coping strategies (breathing, journaling, grounding, movement) when appropriate.
- Be transparent and honest; if you don't know something, say so and suggest next steps.
- Respect healthy boundaries; you are supportive, not a therapist.
- If you detect self-harm or harm to others, recommend contacting trusted adults and helplines immediately."""


def _style_suffix(style: str) -> str:
    s = (style or "friendly").lower()
    if s == "mentor":
        return ("Use a calm, wise mentor tone. Encourage reflection, use gentle metaphors, "
                "and highlight one key insight to remember today.")
    if s == "coach":
        return ("Use an energetic coach tone. Be concise, action-oriented, give 1–2 small steps, "
                "and add gentle accountability for tomorrow.")
    return ("Use a warm, friendly peer tone. Validate feelings, add a tiny spark of humor if appropriate, "
            "and keep sentences short.")

def _mood_hint_line(mood_hint: str | None) -> str:
    return f"User mood context: {mood_hint}" if mood_hint else ""


def gemini_reply(user_text: str, style: str = "friendly", mood_hint: str | None = None) -> str:
    prompt = f"{_system_persona_base}\n{_style_suffix(style)}\n{_mood_hint_line(mood_hint)}\nUser: {user_text}\nReply in 2-4 short sentences."
    response = genai.GenerativeModel(MODEL).generate_content(prompt)
    return (response.text or "").strip()


def reflect_mood(one_line_context: str) -> str:
    prompt = f"Summarize the user's mood in one supportive sentence. Input: {one_line_context}"
    response = genai.GenerativeModel(MODEL).generate_content(prompt)
    return (response.text or "").strip()

def generate_affirmation(history_hint: str) -> str:
    prompt = f"Create a short, specific daily affirmation for a youth based on: {history_hint}. Keep it under 12 words."
    response = genai.GenerativeModel(MODEL).generate_content(prompt)
    return (response.text or "").strip().strip('"')

def classify_crisis(user_text: str) -> dict:
    """
    Returns dict: {"risk": "none"|"medium"|"high", "reason": "..."}
    """
    prompt = f"""Classify the following text for crisis risk:
Text: \"\"\"{user_text}\"\"\"
Respond as JSON with keys risk(one of: none, medium, high) and reason.
If user mentions self-harm/suicidal ideation -> high.
If severe hopelessness -> medium.
Otherwise none.
"""
    response = genai.GenerativeModel(MODEL).generate_content(prompt)
    import json
    try:
        j = json.loads(response.text)
        if j.get("risk") not in ["none","medium","high"]:
            j["risk"] = "none"
        return j
    except Exception:
        return {"risk":"none","reason":"Parser fallback"}

def transcribe_or_understand_audio(file_bytes: bytes, mime_type: str = "audio/wav") -> str:
    """
    Sends audio to Gemini for understanding. Returns a short summary of what the user said/felt.
    """
    model = genai.GenerativeModel(MODEL)
    part = {"mime_type": mime_type, "data": file_bytes}
    resp = model.generate_content(["Summarize the core message and emotion in one sentence:", part])
    return (resp.text or "").strip()
