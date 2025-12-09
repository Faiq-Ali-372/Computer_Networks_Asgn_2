# backend/storage.py
import os
from backend.utils import gen_id, sha256_bytes, write_json, read_json, now_ts

BASE = os.path.abspath(os.path.join(os.getcwd(), "storage"))
UPLOADS = os.path.join(BASE, "uploads")
VIDEOS = os.path.join(BASE, "videos")
INDEX_PATH = os.path.join(BASE, "videos.json")

os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(VIDEOS, exist_ok=True)

def create_upload_session(owner_id, title, total_size, mime="video/mp4"):
    upload_id = gen_id("upload")
    session_dir = os.path.join(UPLOADS, upload_id)
    os.makedirs(session_dir)
    meta = {
        "upload_id": upload_id,
        "owner": owner_id,
        "title": title,
        "mime": mime,
        "created": now_ts(),
        "total_size": int(total_size),
        "received": 0,
        "chunks": []
    }
    write_json(os.path.join(session_dir, "meta.json"), meta)
    return meta

def save_chunk(upload_id, chunk_index, data:bytes):
    session_dir = os.path.join(UPLOADS, upload_id)
    if not os.path.exists(session_dir):
        raise FileNotFoundError("Upload session not found")
    chunk_path = os.path.join(session_dir, f"chunk_{chunk_index:06d}.part")
    with open(chunk_path, "wb") as f:
        f.write(data)
    # update meta
    meta = read_json(os.path.join(session_dir, "meta.json"), {})
    if not meta:
        raise FileNotFoundError("Upload meta missing")
    # prevent duplicate chunk entries
    existing = [c for c in meta.get("chunks", []) if c.get("index") == chunk_index]
    if not existing:
        meta.setdefault("chunks", []).append({"index": chunk_index, "size": len(data), "sha256": sha256_bytes(data)})
    meta["received"] = sum(c["size"] for c in meta.get("chunks", []))
    write_json(os.path.join(session_dir, "meta.json"), meta)
    return True

def commit_upload(upload_id, expected_sha256=None):
    session_dir = os.path.join(UPLOADS, upload_id)
    meta = read_json(os.path.join(session_dir, "meta.json"))
    if not meta:
        raise FileNotFoundError("Upload session not found")
    # sort chunks by index
    chunks = sorted(meta.get("chunks", []), key=lambda c: c["index"])
    out_path = os.path.join(VIDEOS, f"{upload_id}.mp4")
    with open(out_path, "wb") as out:
        for c in chunks:
            p = os.path.join(session_dir, f"chunk_{c['index']:06d}.part")
            if not os.path.exists(p):
                raise FileNotFoundError(f"Missing chunk file: {p}")
            with open(p, "rb") as cf:
                out.write(cf.read())
    # verify final checksum if provided
    if expected_sha256:
        import hashlib
        h = hashlib.sha256()
        with open(out_path, "rb") as f:
            while True:
                b = f.read(8192)
                if not b: break
                h.update(b)
        if h.hexdigest() != expected_sha256:
            raise ValueError("Video checksum mismatch")
    # update index
    index = read_json(INDEX_PATH, default=[])
    video_meta = {
        "video_id": upload_id,
        "title": meta.get("title"),
        "owner": meta.get("owner"),
        "mime": meta.get("mime"),
        "size": os.path.getsize(out_path),
        "path": out_path,
        "created": now_ts()
    }
    index.append(video_meta)
    write_json(INDEX_PATH, index)
    # optional: cleanup upload dir
    return video_meta

def list_videos(owner_id=None):
    index = read_json(INDEX_PATH, default=[])
    if owner_id:
        return [v for v in index if v["owner"] == owner_id]
    return index

def get_video_bytes(video_id, start=None, end=None):
    path = os.path.join(VIDEOS, f"{video_id}.mp4")
    if not os.path.exists(path):
        raise FileNotFoundError("Video not found")
    size = os.path.getsize(path)
    s = 0 if start is None else int(start)
    e = size-1 if end is None else int(end)
    if s > e or e >= size:
        raise ValueError("Range not satisfiable")
    with open(path, "rb") as f:
        f.seek(s)
        return f.read(e - s + 1), s, e, size

def delete_video(video_id, owner_id=None):
    index = read_json(INDEX_PATH, default=[])
    for i, v in enumerate(index):
        if v["video_id"] == video_id:
            if owner_id and v["owner"] != owner_id:
                raise PermissionError("Not owner")
            # delete file
            try:
                os.remove(v["path"])
            except:
                pass
            index.pop(i)
            write_json(INDEX_PATH, index)
            return True
    raise FileNotFoundError("Video not in index")
