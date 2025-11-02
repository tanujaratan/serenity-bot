# utils/auth.py
import os
import requests
import streamlit as st


# --- Helper: Load Firebase Web API key safely ---
def _get_firebase_key() -> str:
    """
    Load Firebase Web API key from Streamlit Secrets or environment.
    Prevents crashes if secrets aren't available yet.
    """
    key = None

    # Try Streamlit secrets first (works on Streamlit Cloud)
    try:
        if "FIREBASE_API_KEY" in st.secrets:
            key = st.secrets["FIREBASE_API_KEY"]
        elif "FIREBASE_WEB_API_KEY" in st.secrets:
            key = st.secrets["FIREBASE_WEB_API_KEY"]
    except Exception:
        # st.secrets might not exist locally
        pass

    # Fallback for local .env
    if not key:
        key = os.getenv("FIREBASE_API_KEY") or os.getenv("FIREBASE_WEB_API_KEY")

    if not key:
        raise RuntimeError(
            "❌ Firebase Web API key missing.\n"
            "Set FIREBASE_API_KEY (or FIREBASE_WEB_API_KEY) in Streamlit Secrets "
            "or your local .env file."
        )

    return key


# --- Helper: POST wrapper with clean Firebase error handling ---
def _post(url: str, data: dict):
    """POST wrapper that reports clean Firebase API errors."""
    try:
        res = requests.post(url, json=data, timeout=20)
        res.raise_for_status()
        return res.json()
    except requests.RequestException:
        try:
            err = res.json()
        except Exception:
            err = {"error": res.text[:300]}
        raise RuntimeError(f"🔥 Firebase Auth failed: {err}")


# --- Auth functions ---
def signup_email_password(email: str, password: str):
    """Sign up a new user with email + password."""
    key = _get_firebase_key()
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={key}"
    return _post(url, {"email": email, "password": password, "returnSecureToken": True})


def login_email_password(email: str, password: str):
    """Login existing user with email + password."""
    key = _get_firebase_key()
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={key}"
    return _post(url, {"email": email, "password": password, "returnSecureToken": True})


def anonymous_signin():
    """Sign in anonymously (no email/password)."""
    key = _get_firebase_key()
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={key}"
    return _post(url, {"returnSecureToken": True})
