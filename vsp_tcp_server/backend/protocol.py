# backend/protocol.py
import re
from typing import Tuple, Dict

CRLF = b"\r\n"
MAX_HEADER_BYTES = 64 * 1024

def read_line(sock) -> bytes:
    buf = bytearray()
    while True:
        ch = sock.recv(1)
        if not ch:
            raise ConnectionError("Socket closed")
        buf += ch
        if buf.endswith(CRLF):
            return bytes(buf[:-2])

def read_exact(sock, n) -> bytes:
    parts = []
    remaining = n
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("Socket closed")
        parts.append(chunk)
        remaining -= len(chunk)
    return b"".join(parts)

def parse_request(sock) -> Tuple[str, str, str, Dict[str,str], bytes]:
    try:
        start_line_bytes = read_line(sock)
        start_line = start_line_bytes.decode('utf-8', errors='replace')
    except ConnectionError:
        raise
    
    if not start_line:
        raise ValueError("Empty start line")
    
    parts = start_line.split()
    if len(parts) < 3:
        # Handle cases where browsers might send slightly malformed Keep-Alive checks
        if len(parts) == 2:
             return parts[0], parts[1], "HTTP/1.1", {}, b""
        raise ValueError(f"Malformed start line: {start_line}")
        
    method, target, version = parts[0], parts[1], parts[2]
    headers = {}
    
    total_header_bytes = 0
    while True:
        line = read_line(sock).decode('utf-8', errors='replace')
        if line == "":
            break
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip()] = v.strip()
        total_header_bytes += len(line)
        if total_header_bytes > MAX_HEADER_BYTES:
            raise ValueError("Headers too large")
            
    body = b""
    if 'Content-Length' in headers:
        try:
            cl = int(headers['Content-Length'])
            if cl > 0:
                body = read_exact(sock, cl)
        except ValueError:
            pass
            
    return method, target, version, headers, body

def build_response(status_code:int, reason:str, headers:dict=None, body:bytes=b"") -> bytes:
    if headers is None:
        headers = {}
    if 'Content-Length' not in headers:
        headers['Content-Length'] = str(len(body))
    
    # FIX: Use HTTP/1.1 so browsers accept the response
    lines = []
    lines.append(f"HTTP/1.1 {status_code} {reason}")
    for k,v in headers.items():
        lines.append(f"{k}: {v}")
    
    # Add CORS/Connection headers for browser stability
    if "Connection" not in headers:
        lines.append("Connection: close")
    lines.append("Access-Control-Allow-Origin: *")
    
    header_block = "\r\n".join(lines) + "\r\n\r\n"
    return header_block.encode('utf-8') + body