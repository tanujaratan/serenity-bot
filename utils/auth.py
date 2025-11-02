# utils/auth.py
import os
import requests

# Accept either name; app.py already copies Secrets -> env
API_KEY = os.environ.get("FIREBASE_API_KEY") or os.environ.get("FIREBASE_WEB_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "Missing Firebase Web API key. Set FIREBASE_API_KEY or FIREBASE_WEB_API_KEY "
        "in Streamlit Secrets (or .env for local dev)."
    )

BASE = "https://identitytoolkit.googleapis.com/v1"

def _url(path: str) -> str:
    return f"{BASE}/{path}?key={API_KEY}"

def signup_email_password(email: str, password: str):
    r = requests.post(_url("accounts:signUp"),
                      json={"email": email, "password": password, "returnSecureToken": True})
    if r.status_code != 200:
        raise RuntimeError(r.json())
    return r.json()

def login_email_password(email: str, password: str):
    r = requests.post(_url("accounts:signInWithPassword"),
                      json={"email": email, "password": password, "returnSecureToken": True})
    if r.status_code != 200:
        raise RuntimeError(r.json())
    return r.json()

def anonymous_signin():
    r = requests.post(_url("accounts:signUp"), json={"returnSecureToken": True})
    if r.status_code != 200:
        raise RuntimeError(r.json())
    return r.json()
