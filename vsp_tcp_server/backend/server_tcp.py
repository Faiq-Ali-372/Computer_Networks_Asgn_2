# backend/server_tcp.py
import socket
import threading
import os
import mimetypes
from backend.protocol import parse_request, build_response
from backend.tcp_core import DISPATCH, authenticate_from_headers
import logging
import inspect

# Configuration
HOST = "0.0.0.0"
PORT = 9080
FRONTEND_DIR = os.path.abspath(os.path.join(os.getcwd(), "frontend"))

logging.basicConfig(level=logging.INFO)

def handle_static(target, headers, body):
    # Map "/" to "index.html"
    if target == "/" or target == "":
        filename = "index.html"
    else:
        filename = target.lstrip("/")
    
    # Security: prevent directory traversal
    if ".." in filename:
        return build_response(403, "Forbidden", {}, b"Access Denied")

    path = os.path.join(FRONTEND_DIR, filename)
    
    if os.path.exists(path) and os.path.isfile(path):
        mime, _ = mimetypes.guess_type(path)
        mime = mime or "application/octet-stream"
        with open(path, "rb") as f:
            data = f.read()
        return build_response(200, "OK", {"Content-Type": mime}, data)
    else:
        return build_response(404, "Not Found", {}, b"404 Not Found")

def handle_client(conn, addr):
    logging.info(f"Connected: {addr}")
    try:
        while True:
            try:
                method, target, version, headers, body = parse_request(conn)
            except (ConnectionError, ValueError):
                break
                
            logging.info(f"REQ: {method} {target}")
            
            # Route Traffic
            if target.startswith("/api/"):
                # API Requests
                api_target = target.replace("/api", "", 1)
                # Map HTTP methods to VSP commands
                handler = None
                
                if method == "POST" and "login" in target: handler = DISPATCH["LOGIN"]
                elif method == "POST" and "newvid" in target: handler = DISPATCH["NEWVID"]
                elif method == "POST" and "upload_chunk" in target: handler = DISPATCH["CHUNK"]
                elif method == "POST" and "commit" in target: handler = DISPATCH["COMMIT"]
                elif method == "GET" and "videos" in target: handler = DISPATCH["LIST"]
                elif method == "GET" and "video/" in target: handler = DISPATCH["GETVID"]
                elif method == "DELETE": handler = DISPATCH.get("DELETE", None) # Not implemented in core yet
                
                # If specific handler not found via URL map, try generic method map (Optional fallback)
                if not handler and method in DISPATCH:
                    handler = DISPATCH[method]

                if handler:
                    user = authenticate_from_headers(headers)
                    try:
                        sig = inspect.signature(handler)
                        if len(sig.parameters) == 3:
                            resp = handler(api_target, headers, body)
                        else:
                            resp = handler(api_target, headers, body, user)
                    except Exception as e:
                        logging.exception("Handler Error")
                        resp = build_response(500, "Server Error", {}, str(e).encode())
                else:
                    resp = build_response(404, "Not Found", {}, b"API Endpoint Not Found")
            else:
                # Static File Requests (Frontend)
                resp = handle_static(target, headers, body)

            conn.sendall(resp)
            
            # Close connection (Simple HTTP/1.0 style behavior for stability)
            break 
    finally:
        conn.close()

def serve():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(50)
    logging.info(f"Server running on http://localhost:{PORT}")
    try:
        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    finally:
        s.close()

if __name__ == "__main__":
    serve()