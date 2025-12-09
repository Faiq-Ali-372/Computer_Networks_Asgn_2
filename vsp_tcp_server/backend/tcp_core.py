# backend/tcp_core.py
from backend.protocol import build_response
from backend.storage import *
from backend.auth import verify_user, issue_token, decode_token, create_user
import json

def _parse_json(body:bytes):
    if not body: return {}
    try: return json.loads(body.decode('utf-8'))
    except: return {}

def handle_LOGIN(target, headers, body):
    payload = _parse_json(body)
    username = payload.get("username")
    password = payload.get("password")
    
    # Auto-register for demo purposes if user doesn't exist
    try:
        create_user(username, password)
    except ValueError:
        pass # User exists, proceed to verify
        
    ok = verify_user(username, password)
    if not ok:
        return build_response(401, "Unauthorized", {}, b'{"message":"Invalid credentials"}')
    token = issue_token(username)
    return build_response(200, "OK", {"Content-Type":"application/json"}, json.dumps({"token":token}).encode())

def handle_NEWVID(target, headers, body, auth_user):
    payload = _parse_json(body)
    title = payload.get("title","untitled")
    size = payload.get("total_size", 0)
    meta = create_upload_session(auth_user, title, size)
    return build_response(201, "Created", {"Content-Type":"application/json"}, json.dumps(meta).encode())

def handle_CHUNK(target, headers, body, auth_user):
    u = headers.get("Upload-Id")
    if not u: return build_response(400, "Bad Request", {}, b'{"message":"Missing Upload-Id"}')
    idx = int(headers.get("Chunk-Index", 0))
    save_chunk(u, idx, body)
    return build_response(200, "OK", {}, b'{"message":"Chunk Received"}')

def handle_COMMIT(target, headers, body, auth_user):
    u = headers.get("Upload-Id")
    try:
        vid = commit_upload(u)
        return build_response(200, "OK", {"Content-Type":"application/json"}, json.dumps(vid).encode())
    except Exception as e:
        return build_response(500, "Error", {}, str(e).encode())

def handle_LIST(target, headers, body, auth_user):
    vids = list_videos(owner_id=auth_user)
    return build_response(200, "OK", {"Content-Type":"application/json"}, json.dumps(vids).encode())

def handle_GETVID(target, headers, body, auth_user):
    parts = target.split("/")
    video_id = parts[-1]
    rng = headers.get("Range")
    
    try:
        if rng:
            m = rng.replace("bytes=", "")
            s_str, e_str = m.split("-", 1)
            # Default logic if end is missing
            s = int(s_str) if s_str else 0
            # If e_str is empty, we don't have an end yet, storage needs to handle it
            data, real_s, real_e, total = get_video_bytes(video_id, s, e_str if e_str else None)
            
            h = {
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes {real_s}-{real_e}/{total}",
                "Accept-Ranges": "bytes"
            }
            return build_response(206, "Partial Content", h, data)
        else:
            data, _, _, _ = get_video_bytes(video_id)
            return build_response(200, "OK", {"Content-Type":"video/mp4"}, data)
    except Exception as e:
        return build_response(404, "Not Found", {}, b'Video not found')

DISPATCH = {
    "LOGIN": handle_LOGIN,
    "NEWVID": handle_NEWVID,
    "CHUNK": handle_CHUNK,
    "COMMIT": handle_COMMIT,
    "LIST": handle_LIST,
    "GETVID": handle_GETVID
}

def authenticate_from_headers(headers):
    auth = headers.get("Authorization")
    if auth and "Bearer " in auth:
        return decode_token(auth.split(" ")[1]).get("sub")
    return None