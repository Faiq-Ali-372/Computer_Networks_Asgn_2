# backend/utils.py
import hashlib
import uuid
import time
import json
import os

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def gen_id(prefix: str="id") -> str:
    return f"{prefix}_{uuid.uuid4().hex}"

def now_ts() -> int:
    return int(time.time())

def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
