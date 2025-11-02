
# --- Safe env & secrets setup (top of app.py) ---
import os
import streamlit as st


def safe_load_dotenv():
    """Safely load local .env if Streamlit secrets not available."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass


# --- Load Firebase / Gemini keys ---
if st.secrets:
    # 1️⃣ Firebase Service Account JSON
    sa = st.secrets.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if sa:
        os.environ["FIREBASE_SERVICE_ACCOUNT_JSON"] = sa

    # 2️⃣ Firebase Web API Key
    fb_key = st.secrets.get("FIREBASE_API_KEY") or st.secrets.get("FIREBASE_WEB_API_KEY")
    if fb_key:
        os.environ["FIREBASE_API_KEY"] = fb_key
        os.environ["FIREBASE_WEB_API_KEY"] = fb_key

    # 3️⃣ Gemini API Key (optional)
    gkey = st.secrets.get("GOOGLE_API_KEY")
    if gkey:
        os.environ["GOOGLE_API_KEY"] = gkey

else:
    safe_load_dotenv()


# Now normal imports
import io, datetime, time, random
import numpy as np
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
from gtts import gTTS

# optional mic recorder
try:
    from streamlit_mic_recorder import mic_recorder
except Exception:
    mic_recorder = None

# rest of imports
from streamlit_drawable_canvas import st_canvas
import streamlit.components.v1 as components

# utils (your modules)
from utils.ai import gemini_reply, reflect_mood, generate_affirmation, classify_crisis, transcribe_or_understand_audio
from utils.auth import signup_email_password, login_email_password, anonymous_signin
from utils.db import (
    log_mood, list_recent_moods, store_letter, due_letters, mark_letter_delivered, update_daily_report,
    add_memory, list_memories, add_schedule_item, list_schedule
)

# ===== basics & helpers (top of file) =====

from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
from streamlit_drawable_canvas import st_canvas

# --- safe stubs if not defined elsewhere ---
if "log_mood" not in globals():
    def log_mood(user_id, mood, note, details):
        st.session_state.setdefault("_mood_log", []).append(
            {"user_id": user_id, "mood": mood, "note": note, "details": details, "ts": time.time()}
        )

if "delete_schedule_item" not in globals():
    def delete_schedule_item(user_id, index_zero_based: int):
        """Fallback only. Replace with your real backend delete if you have one."""
        store = st.session_state.setdefault("_schedule_store", {})
        seq = store.get(user_id)
        if isinstance(seq, list) and 0 <= index_zero_based < len(seq):
            seq.pop(index_zero_based)

# --- doodle helpers ---
def _has_drawing(img):
    if img is None:
        return False
    arr = np.array(img.convert("L"))
    return (arr < 250).any()

def apply_glitter_effect(pil_img):
    """
    Glittery shine:
    - Slight stroke thicken
    - Tiny star sparkles only on drawn areas
    - Soft blur for clean shimmer (not heavy glitter texture)
    """
    base = pil_img.convert("RGBA")
    thicker = base.filter(ImageFilter.MinFilter(size=3))  # subtle thickness

    # mask of inked pixels
    gray = np.array(thicker.convert("L"))
    ys, xs = np.where(gray < 240)

    overlay = Image.new("RGBA", thicker.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    if len(xs) > 0:
        n_sparks = min(80, max(24, len(xs) // 120))
        for _ in range(n_sparks):
            k = random.randrange(len(xs))
            x, y = int(xs[k]), int(ys[k])
            size = random.randint(2, 4)
            alpha = random.randint(90, 160)
            # star cross
            draw.line((x - size, y, x + size, y), fill=(255, 255, 255, alpha), width=1)
            draw.line((x, y - size, x, y + size), fill=(255, 255, 255, alpha), width=1)
            # warm center dot
            draw.ellipse((x-1, y-1, x+1, y+1), fill=(255, 245, 180, alpha))
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=0.8))

    shiny = Image.alpha_composite(thicker, overlay)
    shiny = ImageEnhance.Brightness(shiny).enhance(1.06)
    return shiny

import streamlit.components.v1 as components


st.set_page_config(page_title="Serenity Bot", page_icon="🧘", layout="centered")

# --- Auth ---
def ensure_auth():
    if "user" not in st.session_state:
        st.session_state.user = None
    if st.session_state.user is None:
        st.sidebar.title("Login / Signup")
        mode = st.sidebar.radio("Mode", ["Login", "Signup", "Continue Anonymously"])
        if mode in ["Login", "Signup"]:
            email = st.sidebar.text_input("Email")
            pw = st.sidebar.text_input("Password", type="password")
            if st.sidebar.button(mode):
                try:
                    if mode == "Signup":
                        res = signup_email_password(email, pw)
                    else:
                        res = login_email_password(email, pw)
                    st.session_state.user = {"uid": res["localId"], "email": res.get("email", email)}
                    st.sidebar.success(f"Welcome, {st.session_state.user['email']}!")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(str(e))
        else:
            if st.sidebar.button("Go Anonymous"):
                try:
                    res = anonymous_signin()
                    st.session_state.user = {"uid": res["localId"], "email": None}
                    st.sidebar.success("Signed in anonymously!")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(str(e))
        st.stop()


ensure_auth()
user_id = st.session_state.user["uid"]

# --- Sidebar preferences ---
st.sidebar.header("Preferences")
style = st.sidebar.selectbox("Conversation style", ["friendly", "mentor", "coach"])
st.sidebar.write("---")
st.sidebar.write("Tips: use the tabs below to explore features.")

st.title("🧘 Serenity Bot — Youth Mental Wellness")

tabs = st.tabs(["Chat", "MoodTracker" ,"Breathing Coach", "Letters","insights", "Memory & Schedule Tab" ,"Mini Games"])

# --- Chat Tab ---
with tabs[0]:
    st.subheader("Chat with Serenity")
    st.caption("Record a quick voice note or upload audio, and/or type.")

    rec_cols = st.columns([1, 1])

    # Persistent storage
    if "rec_bytes" not in st.session_state:
        st.session_state.rec_bytes = None

    with rec_cols[0]:
        if mic_recorder is not None:
            audio_data = mic_recorder(
                start_prompt="🎙️ Start recording",
                stop_prompt="⏹️ Stop",
                format="wav",
                just_once=True,
                use_container_width=True,
                key="mic_rec",
            )

            if audio_data and audio_data.get("bytes"):
                # Save audio immediately
                st.session_state.rec_bytes = audio_data["bytes"]
                st.success("🎤 Recording captured successfully!")
                st.audio(st.session_state.rec_bytes, format="audio/wav")
        else:
            st.warning("Microphone recording not available (component not installed).")

    with rec_cols[1]:
        audio = st.file_uploader("Or upload (wav/mp3/m4a)", type=["wav", "mp3", "m4a"])

    text = st.text_area("Type what's on your mind")

    # --- Send Button ---
    if st.button("Send", key="chat_send"):
        content_summary = ""

        # Prefer recorded mic bytes if available
        if st.session_state.rec_bytes:
            with st.spinner("Understanding your recorded audio..."):
                content_summary = transcribe_or_understand_audio(
                    st.session_state.rec_bytes, mime_type="audio/wav"
                )
            st.info(f"🎧 Recorded audio summary: {content_summary}")

        # Uploaded audio
        if audio is not None:
            bytes_data = audio.read()
            ext = audio.name.split(".")[-1].lower()
            mime = "audio/wav" if ext == "wav" else ("audio/mp3" if ext == "mp3" else "audio/m4a")
            with st.spinner("Understanding your uploaded audio..."):
                file_summary = transcribe_or_understand_audio(bytes_data, mime_type=mime)
            st.info(f"📎 Uploaded audio summary: {file_summary}")
            content_summary = (content_summary + " " + file_summary).strip()

        final_text = (text or "") + (" " + content_summary if content_summary else "")
        final_text = final_text.strip()

        if not final_text:
            st.warning("Please provide text or audio.")
        else:
            crisis = classify_crisis(final_text)
            if crisis["risk"] == "high":
                st.error("🚨 It sounds serious. Reach out to AASRA: 91-9820466726 or KIRAN: 1800-599-0019.")
            elif crisis["risk"] == "medium":
                st.warning("You're going through a lot — consider talking to someone you trust ❤️")

            history_for_hint = list_recent_moods(user_id, days=3)
            mood_hint = history_for_hint[-1]["mood"] if history_for_hint else None

            # 🔎 Pull a tiny bit of memory + schedule to guide the reply (few-shot context)
            try:
              mems = list_memories(user_id, limit=10)
              mem_bits = "; ".join([f"{m.get('key')}: {m.get('value')}" for m in mems[-5:]])  # last 5
            except Exception:
              mem_bits = ""

            try:
              sched = list_schedule(user_id)
              # Compact weekly summary, max 3 items to avoid token bloat
              sched_bits = "; ".join([f"{s['title']}({','.join(s['days'])} {s['start_time']}-{s['end_time']})" for s in sched[:3]])
            except Exception:
                sched_bits = ""

            memory_context = ""
            if mem_bits or sched_bits:
               memory_context = f"\n[User facts] {mem_bits}\n[Weekly schedule] {sched_bits}\n"

            prompt_text = (memory_context + final_text).strip()

            with st.spinner("Thinking..."):
               reply = gemini_reply(prompt_text, style=style, mood_hint=mood_hint)



# --- MoodTracker Tab ---
with tabs[1]:
    st.subheader("🪞 Daily Mood, Journal & Reflection")

    col1, col2 = st.columns(2)
    with col1:
        mood = st.selectbox(
            "How are you feeling today?",
            [
                "😊 Happy", "🎉 Excited", "😌 Calm",  # ← added 2 more positive moods
                "🙂 Okay", "😟 Anxious", "😢 Sad", "😠 Angry", "😴 Tired", "🤒 Unwell"
            ]
        )
    with col2:
        note = st.text_input("One-line note (optional)")

    if st.button("💾 Save today's mood"):
        with st.spinner("Reflecting..."):
            reflection = reflect_mood(f"{mood} {note}")
        log_mood(user_id, mood, note, reflection)
        try:
            update_daily_report(user_id)
        except Exception:
            pass
        st.success("Saved! " + reflection)

    st.markdown("### 📊 Your Emotional Journey (Past 14 Days)")
    data = list_recent_moods(user_id, days=14)

    if not data:
        st.info("No data yet. Log a mood above.")
    else:
        df = pd.DataFrame(data)

        # Normalize columns
        if "mood" not in df.columns and "feeling" in df.columns:
            df.rename(columns={"feeling": "mood"}, inplace=True)
        if "date" not in df.columns and "created_at" in df.columns:
            df.rename(columns={"created_at": "date"}, inplace=True)

        # Parse dates
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df.dropna(subset=["date"], inplace=True)
        df.sort_values("date", inplace=True)

        # Map mood → numeric score (add new positives)
        mood_map = {
            "😊 Happy": 5, "🎉 Excited": 5, "😌 Calm": 5,
            "🙂 Okay": 4,
            "😟 Anxious": 2, "😢 Sad": 1, "😠 Angry": 1, "😴 Tired": 2, "🤒 Unwell": 1,
            "⭐ Good Deed": 5, "🙏 Gratitude": 5,
        }
        df["score"] = df["mood"].map(mood_map).fillna(3)

        # 🎨 Mood color map (add colors for new moods)
        color_map = {
            "😊 Happy": "#FFD93B",
            "🎉 Excited": "#FF6B6B",
            "😌 Calm": "#7DD3FC",
            "🙂 Okay": "#87CEEB",
            "😟 Anxious": "#FFB347",
            "😢 Sad": "#9CA3AF",
            "😠 Angry": "#EF4444",
            "😴 Tired": "#A78BFA",
            "🤒 Unwell": "#60A5FA",
            "⭐ Good Deed": "#34D399",
            "🙏 Gratitude": "#FACC15",
        }

        # Extract emoji & tooltips
        df["emoji"] = df["mood"].str.extract(r'([^\w\s])')
        df["tooltip"] = df.apply(lambda r: f"{r['emoji']} {r['mood']} — {r.get('note','')}", axis=1)

        # --- 🌈 Emotional Mood Timeline ---
        st.write("#### 🌈 Mood Journey (Last 14 Days)")
        fig = px.scatter(
            df,
            x="date",
            y="score",
            color="mood",
            color_discrete_map=color_map,
            text="emoji",
            hover_name="tooltip",
            size=[18]*len(df),
            title=None,
        )

        # Smooth connecting line
        fig.add_scatter(
            x=df["date"],
            y=df["score"].rolling(2, min_periods=1).mean(),
            mode="lines",
            line=dict(color="#9CA3AF", width=2, dash="dot"),
            name="Mood Flow",
        )

        fig.update_traces(
            textposition="middle center",
            marker=dict(opacity=0.8, line=dict(width=0))
        )
        fig.update_layout(
            yaxis=dict(title="Mood Intensity (1–5)", range=[0, 5.5]),
            xaxis_title="Date",
            plot_bgcolor="white",
            paper_bgcolor="white",
            showlegend=False,
            font=dict(size=14),
            height=400,
            margin=dict(l=30, r=30, t=30, b=30),
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- 🌟 Mood Summary ---
        avg_score = df["score"].mean()
        dominant = df["mood"].value_counts().idxmax()
        st.success(f"💫 You've mostly felt *{dominant}* with an average mood of {avg_score:.1f}/5")

        # --- 🧭 Mood Distribution ---
        st.write("#### 🧭 Mood Distribution (Past 14 Days)")
        counts = df["mood"].value_counts().reset_index()
        counts.columns = ["mood", "count"]
        bar = px.bar(counts, x="mood", y="count", color="mood",
                     color_discrete_map=color_map, title=None)
        bar.update_layout(showlegend=False, plot_bgcolor="white", height=300)
        st.plotly_chart(bar, use_container_width=True)

        # --- ⬇️ Export Mood Data (timezone-proof) ---
        from io import BytesIO
        buf = BytesIO()

        def _coerce_for_excel(series: pd.Series) -> pd.Series:
            """
            Make any datetime/timestamp-like column Excel-safe:
            - Remove timezone if it's a pandas datetime64
            - If it's a Firestore/Python datetime object, stringify with .isoformat()
            """
            # Case 1: proper pandas datetime64
            if pd.api.types.is_datetime64_any_dtype(series):
                try:
                    return pd.to_datetime(series, errors="coerce").dt.tz_localize(None)
                except Exception:
                    return series.astype(str)

            # Case 2: object dtype that may contain datetime-like objects
            if series.dtype == "object":
                def _fix_obj(x):
                    try:
                        if hasattr(x, "tzinfo") and x.tzinfo is not None:
                            try:
                                return x.replace(tzinfo=None).isoformat()
                            except Exception:
                                return str(x)
                        if hasattr(x, "isoformat"):
                            return x.isoformat()
                    except Exception:
                        pass
                    return x
                return series.apply(_fix_obj)

            return series

        df_export = df.copy()

        # Ensure "date" is plain YYYY-MM-DD text
        if "date" in df_export.columns:
            df_export["date"] = pd.to_datetime(df_export["date"], errors="coerce").dt.strftime("%Y-%m-%d")

        # Sanitize ALL columns for Excel
        for c in df_export.columns:
            df_export[c] = _coerce_for_excel(df_export[c])

        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df_export.to_excel(writer, index=False)

        buf.seek(0)
        with st.expander("⬇️ Export mood data"):
            st.download_button(
                label="Download Excel",
                data=buf.getvalue(),
                file_name="moods_last_14_days.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    # --- 🌿 Adaptive Affirmations ---
    st.markdown("---")
    st.subheader("🌿 Personalized Daily Affirmation")

    history = list_recent_moods(user_id, days=7)
    if history:
        moods = [h["mood"] for h in history]
        hint = "based on recent moods: " + ", ".join(moods)
        last_mood = moods[-1]
    else:
        hint = "no prior mood data"
        last_mood = None

    if last_mood in ["😢 Sad", "😟 Anxious", "😠 Angry", "🤒 Unwell"]:
        st.caption("💌 You seem to be going through a rough patch — here's something comforting.")
    elif last_mood in ["😊 Happy", "🎉 Excited", "😌 Calm", "🙏 Gratitude", "⭐ Good Deed"]:
        st.caption("🌞 Keep your positive energy flowing! Here's your affirmation.")
    else:
        st.caption("🌿 Reflect on yourself with a gentle thought today.")

    if st.button("✨ Generate Affirmation"):
        with st.spinner("Creating your personalized affirmation..."):
            aff = generate_affirmation(hint)
        st.success(f"💫 {aff}")

# --- Breathing Coach Tab ---
with tabs[2]:
    st.subheader("Box Breathing (4–4–4)")
    st.caption("Inhale 4 • Hold 4 • Exhale 4 • Hold 4")

    # Controls
    c1, c2 = st.columns(2)
    with c1:
        show_circle = st.toggle("Show animated circle", value=True, help="Old minimize/maximize style")
    with c2:
        music_on = st.toggle("Play calm music", value=False, help="Off by default to avoid autoplay issues")

    # --- Animated circle (classic 'minimize/maximize' look) ---
    if show_circle:
        # You can tweak size with the slider
        size = st.slider("Circle size", 120, 400, 240, step=10)
        speed = st.slider("Breath speed (seconds per phase)", 3, 8, 4, step=1)

        circle_html = f"""
        <div style="display:flex;flex-direction:column;align-items:center;gap:10px;">
          <div id="breath-circle"
               style="
                 width:{size}px;height:{size}px;border-radius:50%;
                 background: radial-gradient( circle at 30% 30%, #8bd3ff, #4aa3ff );
                 box-shadow: 0 10px 30px rgba(0,0,0,.15);
                 transform: scale(0.75);
                 transition: transform {speed}s ease-in-out;
               ">
          </div>
          <div id="breath-text" style="font-family:system-ui,Segoe UI,Roboto,Arial;color:#333;font-size:18px;">
            Inhale…
          </div>
        </div>
        <script>
          const circle = document.getElementById('breath-circle');
          const text = document.getElementById('breath-text');
          const phase = {speed} * 1000;
          // Phases: Inhale (grow) → Hold → Exhale (shrink) → Hold
          let t = 0;
          function step() {{
            const mod = t % 4;
            if (mod === 0) {{
              circle.style.transform = 'scale(1.00)';
              text.textContent = 'Inhale…';
            }} else if (mod === 1) {{
              text.textContent = 'Hold…';
            }} else if (mod === 2) {{
              circle.style.transform = 'scale(0.75)';
              text.textContent = 'Exhale…';
            }} else {{
              text.textContent = 'Hold…';
            }}
            t++;
          }}
          step();
          setInterval(step, phase);
        </script>
        """
        st.components.v1.html(circle_html, height=size+120)

    st.info("Try 3–5 cycles. Notice how your body feels.")

    # --- Background music (opt-in, only when this tab is active) ---
    import base64, os
    if music_on:
        if "breath_audio_bytes" not in st.session_state:
            default_path = os.path.join("assets", "breath.mp3")
            if os.path.exists(default_path):
                st.session_state.breath_audio_bytes = open(default_path, "rb").read()
            else:
                up = st.file_uploader("Upload MP3 (optional)", type=["mp3"], key="upl_breath")
                if up: st.session_state.breath_audio_bytes = up.read()

        if "breath_audio_bytes" in st.session_state:
            b64 = base64.b64encode(st.session_state.breath_audio_bytes).decode("utf-8")
            audio_html = f"""
            <audio id="bgm" autoplay loop playsinline>
              <source src="data:audio/mpeg;base64,{b64}" type="audio/mpeg">
            </audio>
            <script>
              const audio = document.getElementById('bgm');
              // Try to play; if blocked, show a small button
              (async () => {{
                try {{
                  await audio.play();
                }} catch (e) {{
                  if (!document.getElementById('enable-audio-btn')) {{
                    const btn = document.createElement('button');
                    btn.id = 'enable-audio-btn';
                    btn.textContent = "▶ Click to enable sound";
                    btn.style = "padding:8px 12px;margin-top:8px;border-radius:8px;border:1px solid #ddd;cursor:pointer;";
                    btn.onclick = async () => {{ try {{ await audio.play(); btn.remove(); }} catch (err) {{ console.log(err); }} }};
                    document.body.appendChild(btn);
                  }}
                }}
              }})();
              // Pause if user navigates away (another rerun/tab change)
              window.addEventListener('beforeunload', () => {{ try {{ audio.pause(); }} catch (e) {{}} }});
              document.addEventListener('visibilitychange', () => {{
                if (document.hidden) {{ try {{ audio.pause(); }} catch(e){{}} }}
              }});
            </script>
            """
            st.components.v1.html(audio_html, height=0)
        else:
            st.caption("Load music by placing assets/breath.mp3 or uploading an MP3.")

# --- Letters Tab ---
with tabs[3]:
    st.subheader("Write a letter to your future self")
    content = st.text_area("Write from the heart... (only you can see this)")
    default_date = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    deliver_on = st.date_input("Deliver to me on", value=datetime.date.fromisoformat(default_date))

    if st.button("Save Letter"):
        store_letter(user_id, content, deliver_on.isoformat())
        st.success(f"Saved! I'll show this back to you on or after {deliver_on.isoformat()}.")

    st.write("### Letters ready for you")
    due = due_letters(user_id)
    if due:
        for item in due:
            with st.expander(f"Letter from {item['deliver_on']}"):
                st.write(item["content"])
                if st.button("Mark as read", key=item["id"]):
                    mark_letter_delivered(item["id"])
                    st.success("Marked delivered.")
                    st.rerun()
    else:
        st.info("No letters due yet.")

# --- Insights Tab ---
with tabs[4]:
    st.subheader("📈 Daily Insights (last 30 days)")

    # 1) Pull data (30d so it feels more useful than 14)
    raw = list_recent_moods(user_id, days=30)

    if not raw:
        st.info("Log moods to see insights.")
        st.stop()

    # 2) Build DataFrame and normalize dates safely
    df = pd.DataFrame(raw)

    # Try to assemble a reliable datetime column "dt":
    # - Prefer explicit string 'date' (YYYY-MM-DD) from our db.py
    # - Else try Firestore Timestamp 'ts'
    # - Else try 'created_at'
    def _coerce_dt(row):
        # a) fast path: yyyy-mm-dd string
        d = row.get("date")
        if isinstance(d, str) and len(d) >= 10:
            try:
                return pd.to_datetime(d, errors="coerce")
            except Exception:
                pass
        # b) Firestore Timestamp-like object (has .to_datetime or .isoformat or is datetime)
        for k in ("ts", "created_at"):
            t = row.get(k)
            if t is None:
                continue
            # pandas handles python datetimes and numpy datetimes
            try:
                return pd.to_datetime(t, errors="coerce")
            except Exception:
                # last resort: str → to_datetime
                try:
                    return pd.to_datetime(str(t), errors="coerce")
                except Exception:
                    pass
        return pd.NaT

    df["dt"] = df.apply(_coerce_dt, axis=1)
    df.dropna(subset=["dt"], inplace=True)
    if df.empty:
        st.info("I fetched moods but couldn't parse their dates. Try logging one new mood now, then come back here.")
        st.stop()

    df.sort_values("dt", inplace=True)

    # 3) Score mapping (keep in sync with MoodTracker)
    mood_map = {
        "😊 Happy": 5, "🎉 Excited": 5, "😌 Calm": 5,
        "🙂 Okay": 4,
        "😟 Anxious": 2, "😢 Sad": 1, "😠 Angry": 1, "😴 Tired": 2, "🤒 Unwell": 1,
        "⭐ Good Deed": 5, "🙏 Gratitude": 5,
    }
    df["score"] = df["mood"].map(mood_map).fillna(3)

    # 4) KPIs
    last30_avg = df["score"].mean()
    most_common = df["mood"].value_counts().idxmax()

    # Streak: consecutive days with any entry (from most recent backwards)
    dailies = df.groupby(df["dt"].dt.date).agg(avg=("score", "mean")).reset_index()
    dailies.sort_values("dt", inplace=True)
    # compute streak ending today
    today = pd.Timestamp(pd.Timestamp.today().date())
    dates_set = set(pd.to_datetime(dailies["dt"]).dt.date.tolist())
    streak = 0
    cur = today
    while cur.date() in dates_set:
        streak += 1
        cur = cur - pd.Timedelta(days=1)

    c1, c2, c3 = st.columns(3)
    c1.metric("Avg mood (30d)", f"{last30_avg:.2f}/5")
    c2.metric("Most frequent mood", most_common)
    c3.metric("Daily logging streak", f"{streak} days")

    # 5) Weekly average trend (week starts Monday)
    df["week"] = df["dt"].dt.to_period("W-MON").apply(lambda r: r.start_time)
    weekly = df.groupby("week", observed=False)["score"].mean().reset_index()
    line = px.line(weekly, x="week", y="score", markers=True, title="Weekly Average Mood")
    line.update_layout(yaxis=dict(range=[0, 5.5]), plot_bgcolor="white", paper_bgcolor="white", height=320, margin=dict(l=20,r=20,t=40,b=20))
    st.plotly_chart(line, use_container_width=True)

    # 6) Weekday heatmap (how your mood varies by day of week)
    df["weekday"] = df["dt"].dt.day_name()
    wmap = (df.groupby("weekday", observed=False)["score"].mean()
              .reindex(["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]))
    heat_df = pd.DataFrame({"weekday": wmap.index, "avg_score": wmap.values})
    heat = px.bar(heat_df, x="weekday", y="avg_score", title="Average Mood by Weekday", range_y=[0,5.5])
    heat.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white", height=300, margin=dict(l=20,r=20,t=40,b=20))
    st.plotly_chart(heat, use_container_width=True)

    # 7) Small wins / prompts
    pos_days = (dailies["avg"] >= 4.5).sum()
    tough_days = (dailies["avg"] <= 2.0).sum()
    if pos_days:
        st.success(f"🌞 {pos_days} super-positive day(s) in the last month — keep doing what works!")
    if tough_days:
        st.info(f"💪 {tough_days} tough day(s). Check your Breathing Coach or add a Good Deed to nudge momentum.")

    # 8) Optional debug (so you never get stuck wondering why it's empty)
    with st.expander("🛠️ Debug: show parsed moods"):
        st.write(f"Loaded rows: {len(df)}")
        st.dataframe(df[["dt","mood","note","score"]].tail(20), use_container_width=True)


# --- Memory & Schedule Tab ---
with tabs[5]:
    st.subheader("🧠 Memory & Schedule (helps me help YOU)")

    # ========================================
    # 📌 Personal Facts / Memories
    # ========================================
    st.markdown("### 📌 Personal Facts I Should Remember")

    mcol1, mcol2 = st.columns([3, 2])
    with mcol1:
        m_key = st.text_input("Fact title", placeholder="e.g., Dance class, Drama club, Family type...")
        m_value = st.text_area("Details I should remember", placeholder="e.g., Bharatanatyam on Mon/Wed/Fri 6–7:30 PM")
    with mcol2:
        m_tags = st.text_input("Tags (comma separated, optional)", help="e.g., dance, family, project")
        m_importance = st.slider("Importance", 1, 5, 3)
        m_exp = st.text_input("Expires on (optional YYYY-MM-DD)", value="")

    if st.button("➕ Save to Memory"):
        tags = [t.strip() for t in m_tags.split(",") if t.strip()] if m_tags else []
        exp = m_exp.strip() or None
        add_memory(user_id, m_key, m_value, tags=tags, importance=m_importance, expires_on=exp)
        st.success("💾 Saved to memory!")
        st.rerun()

    mems = list_memories(user_id, limit=200)
    if mems:
        st.caption("🧩 What I currently remember about you:")
        for mem in mems[-8:][::-1]:  # last 8
            st.write(f"• **{mem.get('key', '(no key)')}** — {mem.get('value', '')}")
            if mem.get("tags"):
                st.caption("🏷️ " + ", ".join(mem["tags"]))
    else:
        st.info("No memories yet. Add your interests, classes, or habits so I can personalize better!")

    st.divider()

    # ========================================
    # 🗓️ Weekly Schedule (with working delete)
    # ========================================
    st.markdown("### 🗓️ Weekly Schedule (for clash-aware suggestions)")

    # local cache so delete reflects instantly
    if "_schedule_cache" not in st.session_state:
        try:
            st.session_state._schedule_cache = list_schedule(user_id) or []
        except Exception:
            st.session_state._schedule_cache = []

    def _get_schedule():
        return st.session_state.get("_schedule_cache", [])

    def _set_schedule(new_list):
        st.session_state._schedule_cache = new_list

    scol1, scol2 = st.columns(2)
    with scol1:
        s_title = st.text_input("Activity", placeholder="e.g., Bharatanatyam class")
        s_days = st.multiselect("Days", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], default=["Mon", "Wed", "Fri"])
        s_priority = st.slider("Priority (1 = low, 5 = high)", 1, 5, 3)
    with scol2:
        s_start = st.text_input("Start (24h HH:MM)", value="18:00")
        s_end = st.text_input("End (24h HH:MM)", value="19:30")
        s_travel = st.number_input("Travel time after (minutes)", min_value=0, max_value=240, value=0, step=5)

    s_loc = st.text_input("Location (optional)")
    s_notes = st.text_input("Notes (optional)", placeholder="e.g., Teacher name, travel notes…")

    if st.button("➕ Add to Weekly Schedule"):
        try:
            add_schedule_item(
                user_id,
                s_title, s_days, s_start, s_end,
                location=s_loc, notes=s_notes,
                priority=s_priority, travel_mins=int(s_travel)
            )
            # update cache immediately
            local = _get_schedule()
            local.append({
                "title": s_title, "days": s_days,
                "start_time": s_start, "end_time": s_end,
                "priority": int(s_priority), "travel_mins": int(s_travel),
                "location": s_loc, "notes": s_notes,
            })
            _set_schedule(local)
            st.success("✅ Added to weekly schedule!")
            st.rerun()
        except Exception as e:
            st.error(f"⚠️ Invalid input. Details: {e}")

    schedule = _get_schedule()
    if schedule:
        st.markdown("#### 📋 Your Weekly Activities")
        sdf = pd.DataFrame(schedule)
        cols = ["title", "days", "start_time", "end_time", "priority", "travel_mins", "location", "notes"]
        show = sdf[[c for c in cols if c in sdf.columns]]
        st.dataframe(show, use_container_width=True)

        # Delete one entry (numbered)
        st.markdown("##### 🧹 Delete one entry")
        numbered = []
        for idx, rec in enumerate(schedule, start=1):
            titled = rec.get("title", "(untitled)")
            days = ",".join(rec.get("days", []))
            tslot = f"{rec.get('start_time','??:??')}–{rec.get('end_time','??:??')}"
            numbered.append(f"{idx}. {titled} — {days} {tslot}")

        if numbered:
            st.caption("Pick the number you want to remove:")
            del_num = st.number_input("Item number to delete", min_value=1, max_value=len(numbered), value=1, step=1)
            st.code("\n".join(numbered), language="text")

            if st.button("🗑️ Delete selected item"):
                zero_idx = int(del_num) - 1
                try:
                    new_list = [rec for i, rec in enumerate(schedule) if i != zero_idx]
                    _set_schedule(new_list)
                    st.success(f"Deleted item #{int(del_num)}.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not delete item #{int(del_num)}. Details: {e}")

        # Clash Detection
        st.markdown("#### 🔎 Check for Clashes and Get Suggestions")

        if st.button("Find time clashes"):
            def _to_minutes(tstr: str):
                h, m = map(int, tstr.split(":"))
                return h * 60 + m

            rows = []
            for rec in schedule:
                for d in rec.get("days", []):
                    rows.append({
                        "day": d,
                        "title": rec["title"],
                        "start": _to_minutes(rec["start_time"]),
                        "end": _to_minutes(rec["end_time"]),
                        "priority": int(rec.get("priority", 3)),
                        "travel": int(rec.get("travel_mins", 0)),
                    })

            from itertools import combinations
            found_any = False
            for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
                items = [r for r in rows if r["day"] == d]
                items.sort(key=lambda r: r["start"])

                # direct overlaps
                for a, b in combinations(items, 2):
                    overlap = (a["end"] > b["start"]) and (b["end"] > a["start"])
                    if overlap:
                        found_any = True
                        st.warning(f"🕓 {d}: '{a['title']}' and '{b['title']}' overlap. Adjust timing.")

                # travel gap
                for i in range(len(items) - 1):
                    cur, nxt = items[i], items[i + 1]
                    if cur["end"] + cur["travel"] > nxt["start"]:
                        found_any = True
                        st.info(f"🚗 {d}: Not enough travel gap from '{cur['title']}' → '{nxt['title']}'.")

            if not found_any:
                st.success("✅ No overlaps or travel-time conflicts found. Your schedule looks great!")
    else:
        st.info("Add at least one activity to enable clash detection.")


# --- Mini Games Tab ---
with tabs[6]:
    import io, time, random, numpy as np
    from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
    try:
        from streamlit_drawable_canvas import st_canvas
    except Exception:
        st.error("Install first:  pip install streamlit-drawable-canvas==0.9.3")
        st.stop()

    # ------------------ Mini Game: Gratitude Picker ------------------
    st.subheader("Mini Game: Gratitude Picker")
    st.write("Pick 3 things you feel grateful for today.")
    options = ["Family","Friends","Health","Food","Music","Nature","Learning","Creativity","Freedom","Kindness"]
    picked = st.multiselect("Choose any 3", options, max_selections=3)

    uid_safe = st.session_state.get("user_id", user_id if "user_id" in locals() else "guest")
    if st.button("Save Gratitude", key="gratitude_save"):
        note = "Grateful for: " + ", ".join(picked) if picked else "Grateful practice opened."
        log_mood(uid_safe, "🙏 Gratitude", note, "Practiced gratitude.")
        st.success("Saved. Gratitude boosts resilience!")

    st.write("---")

    # ------------------ 🎴 Emoji Memory Match ------------------
    st.subheader("🎴 Emoji Memory Match")
    st.caption("Flip two cards. Match the pair. Clear the board in the fewest moves and time!")

    if "mm_board" not in st.session_state:
        emojis = ["🐶","🐱","🦊","🐼","🐵","🦄","🐸","🐯","🍉","🍓","🍒","🍋","🍇","🍑","🍍","🥝"]
        chosen = random.sample(emojis, 8)
        board = chosen + chosen
        random.shuffle(board)
        st.session_state.mm_board    = board
        st.session_state.mm_matched  = set()
        st.session_state.mm_selected = []
        st.session_state.mm_moves    = 0
        st.session_state.mm_start_ts = time.time()
        st.session_state.mm_done_s   = None
        st.session_state.mm_best     = st.session_state.get("mm_best", None)

    def _reset_memory():
        random.shuffle(st.session_state.mm_board)
        st.session_state.mm_matched  = set()
        st.session_state.mm_selected = []
        st.session_state.mm_moves    = 0
        st.session_state.mm_start_ts = time.time()
        st.session_state.mm_done_s   = None

    c1, c2, c3 = st.columns(3)
    with c1:
        elapsed = int((st.session_state.mm_done_s or time.time()) - st.session_state.mm_start_ts)
        st.metric("⏱ Time", f"{elapsed}s")
    with c2:
        st.metric("🧮 Moves", str(st.session_state.mm_moves))
    with c3:
        if st.button("🔁 New Game", key="mm_new"):
            _reset_memory()
            st.rerun()

    board = st.session_state.mm_board
    cols_per_row = 4
    for r in range(0, len(board), cols_per_row):
        cols = st.columns(cols_per_row)
        for i, col in enumerate(cols, start=r):
            if i >= len(board): 
                continue
            with col:
                is_matched  = i in st.session_state.mm_matched
                is_selected = i in st.session_state.mm_selected
                face = board[i] if (is_matched or is_selected) else "❓"
                disabled = is_matched or is_selected or st.session_state.mm_done_s is not None

                if st.button(face, key=f"mm_card_{i}", disabled=disabled):
                    st.session_state.mm_selected.append(i)
                    if len(st.session_state.mm_selected) == 2:
                        a, b = st.session_state.mm_selected
                        st.session_state.mm_moves += 1
                        if board[a] == board[b]:
                            st.session_state.mm_matched.update({a, b})
                            st.session_state.mm_selected = []
                            if len(st.session_state.mm_matched) == len(board):
                                st.session_state.mm_done_s = time.time()
                        else:
                            st.rerun()

    if len(st.session_state.mm_selected) == 2:
        if st.button("🙈 Hide mismatch", key="mm_hide", help="Click to continue"):
            st.session_state.mm_selected = []
            st.rerun()

    if st.session_state.mm_done_s is not None:
        final_secs = int(st.session_state.mm_done_s - st.session_state.mm_start_ts)
        st.success(f"🎉 You cleared the board in {st.session_state.mm_moves} moves and {final_secs}s!")

    st.write("---")

    # ------------------ 🎨 Doodle & De-Stress (VISIBLE) ------------------
    st.subheader("🎨 Doodle & De-Stress")
    st.caption("Draw freely. Use the toolbar (pen / eraser / undo). Toggle ✨ sparkle if you like.")

    # Make the canvas obviously visible (border, bg, shadow)
    st.markdown("""
        <style>
        div[data-testid="stCanvas"] {padding:8px !important;}
        div[data-testid="stCanvas"] canvas {
            display:block !important;
            background:#f8f6ff !important;     /* pastel bg so it's not 'invisible' */
            border:2px solid #d3c7ff !important;
            border-radius:12px !important;
            box-shadow:0 6px 18px rgba(0,0,0,.08) !important;
        }
        </style>
    """, unsafe_allow_html=True)

    CANVAS_W, CANVAS_H = 820, 420
    stroke_width = st.slider("Stroke width", 2, 14, 4, key="dw")
    stroke_color = st.color_picker("Stroke color", "#111111", key="dc")
    sparkle_on   = st.toggle("✨ Add Sparkle", value=False, key="ds")

    # If the canvas ever fails to mount, changing this key forces a remount.
    canvas_key = st.number_input("Canvas key (touch only if canvas hides)", 1, 9999, value=1, step=1, key="dk")

    canvas = st_canvas(
        fill_color="rgba(0,0,0,0)",
        stroke_width=int(stroke_width),
        stroke_color=stroke_color,
        background_color="#f8f6ff",
        width=CANVAS_W,
        height=CANVAS_H,
        drawing_mode="freedraw",
        display_toolbar=True,
        update_streamlit=True,
        key=f"doodle_{canvas_key}",
    )

    # Small, reliable glitter
    def _has_drawing(img: Image.Image | None) -> bool:
        if img is None: return False
        return (np.array(img.convert("L")) < 250).any()

    def _sparkle(img: Image.Image) -> Image.Image:
        base = img.convert("RGBA")
        blur = base.filter(ImageFilter.GaussianBlur(1.6))
        base = Image.blend(base, blur, 0.25)
        gray = np.array(base.convert("L"))
        ys, xs = np.where(gray < 235)
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        draw = ImageDraw.Draw(overlay)
        if len(xs) > 0:
            n = min(70, max(24, len(xs)//140))
            for _ in range(n):
                k = random.randrange(len(xs))
                x, y = int(xs[k]), int(ys[k])
                draw.ellipse((x-1, y-1, x+1, y+1), fill=(255,245,190,180))
        return Image.alpha_composite(base, overlay)

    if canvas.image_data is not None:
        img = Image.fromarray(canvas.image_data.astype("uint8"))
        if _has_drawing(img):
            if sparkle_on:
                img = _sparkle(img)
            out = io.BytesIO()
            img.save(out, format="PNG")
            out.seek(0)
            st.session_state["doodle_png"] = out.getvalue()
            st.success("🧑‍🎨 Doodle saved!")
        else:
            st.session_state.pop("doodle_png", None)

    st.download_button(
        "📥 Download doodle",
        data=st.session_state.get("doodle_png", b""),
        file_name="doodle.png",
        mime="image/png",
        disabled=("doodle_png" not in st.session_state),
        use_container_width=True,
        key="doodle_download",
    )
