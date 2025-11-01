
import os, requests, json
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("FIREBASE_WEB_API_KEY")

def signup_email_password(email: str, password: str):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
    r = requests.post(url, json={"email":email,"password":password,"returnSecureToken":True})
    if r.status_code != 200:
        raise RuntimeError(r.json())
    return r.json()  # contains idToken, localId, etc.

def login_email_password(email: str, password: str):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    r = requests.post(url, json={"email":email,"password":password,"returnSecureToken":True})
    if r.status_code != 200:
        raise RuntimeError(r.json())
    return r.json()

def anonymous_signin():
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
    r = requests.post(url, json={"returnSecureToken":True})
    if r.status_code != 200:
        raise RuntimeError(r.json())
    return r.json()

