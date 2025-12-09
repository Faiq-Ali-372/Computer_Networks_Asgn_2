# backend/auth.py
import bcrypt
import jwt
import time
import os
from backend.utils import read_json, write_json, now_ts

SECRET = os.environ.get("VSP_SECRET","dev-secret-change-this")
USERS_PATH = os.path.join(os.getcwd(), "storage", "users.json")

def _load_users():
    return read_json(USERS_PATH, default={})

def _save_users(u):
    write_json(USERS_PATH, u)

def create_user(username, password):
    users = _load_users()
    if username in users:
        raise ValueError("User exists")
    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    users[username] = {"password": pw_hash, "created": now_ts()}
    _save_users(users)
    return True

def verify_user(username, password):
    users = _load_users()
    user = users.get(username)
    if not user:
        return False
    return bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8'))

def issue_token(username, lifetime_seconds=3600):
    payload = {"sub": username, "iat": now_ts(), "exp": now_ts()+lifetime_seconds}
    token = jwt.encode(payload, SECRET, algorithm="HS256")
    # pyjwt returns str in modern versions
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token

def decode_token(token):
    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
        return payload
    except Exception as e:
        return None
