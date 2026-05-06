import os
import json
import time
import requests
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# BIFROST SECURE AUTH ENGINE (V1 FINAL - VERCEL RELAY)
# Optimized for serverless execution and bypassing network blocks.

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
AUTH_CHANNEL_ID = os.getenv("AUTH_CHANNEL_ID", "").strip()
ADMIN_KEY = os.getenv("ADMIN_KEY", "").strip()
ADMIN_OPERATOR = os.getenv("ADMIN_OPERATOR", "ADMIN")

def discord_request(url, method="GET", body=None):
    if not DISCORD_TOKEN: return 500, "MISSING_TOKEN"
    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        if method.upper() == "POST":
            res = requests.post(url, json=body, headers=headers, timeout=10)
        else:
            res = requests.get(url, headers=headers, timeout=10)
        return res.status_code, res.json() if res.status_code == 200 else res.text
    except Exception as e:
        return 500, str(e)

def fetch_keys():
    if not AUTH_CHANNEL_ID: return {}, []
    url = f"https://discord.com/api/v10/channels/{AUTH_CHANNEL_ID}/messages?limit=100"
    code, messages = discord_request(url)
    keys = {}
    raw = []
    now = time.time()
    
    if code == 200 and isinstance(messages, list):
        for msg in messages:
            content = msg.get("content", "")
            raw.append({
                "content": content, 
                "timestamp": msg.get("timestamp"), 
                "id": msg.get("id")
            })
            
            if "KEY:" in content:
                try:
                    parts = content.split("|")
                    k = parts[0].replace("KEY:", "").strip()
                    op = parts[1].replace("OP:", "").strip() if len(parts) > 1 else "OPERATOR"
                    
                    # Parse Role and Expiration
                    role = "operator"
                    expires = 0
                    for p in parts:
                        p = p.strip()
                        if p.startswith("ROLE:"):
                            role = p.replace("ROLE:", "").strip().lower()
                        if p.startswith("EXPIRES:"):
                            try: expires = int(p.replace("EXPIRES:", "").strip())
                            except: expires = 0
                    
                    # Skip expired keys
                    if expires > 0 and expires < now:
                        continue
                        
                    keys[k] = {"operator_id": op, "status": "active", "role": role, "expires": expires}
                except: continue
    return keys, raw

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Key')
        self.end_headers()

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        action = query.get('action', ['verify'])[0]
        pass_key = query.get('pass', [None])[0]
        
        if action == 'verify':
            if ADMIN_KEY and pass_key == ADMIN_KEY:
                self._json(200, {"status": "success", "data": {"operator_id": ADMIN_OPERATOR, "role": "commander"}})
            else:
                keys, _ = fetch_keys()
                if pass_key in keys:
                    self._json(200, {"status": "success", "data": keys[pass_key]})
                else:
                    self._json(400, {"status": "error", "message": "INVALID_KEY"})

        elif action == 'list':
            if self.headers.get('X-Admin-Key') == ADMIN_KEY:
                _, raw = fetch_keys()
                self._json(200, {"status": "success", "keys": raw})
            else:
                self._json(401, {"error": "UNAUTHORIZED"})

    def do_POST(self):
        if self.headers.get('X-Admin-Key') != ADMIN_KEY:
            self._json(401, {"error": "UNAUTHORIZED"}); return

        try:
            cl = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(cl))
            new_key = body.get('key')
            op = body.get('operator', 'OPERATOR')
            role = body.get('role', 'operator')
            duration = body.get('expires', 0) # This is the timestamp from the frontend

            if not new_key: self._json(400, {"error": "MISSING_KEY"}); return

            msg_content = f"KEY: {new_key} | OP: {op} | ROLE: {role} | EXPIRES: {duration}"
            url = f"https://discord.com/api/v10/channels/{AUTH_CHANNEL_ID}/messages"
            code, res_body = discord_request(url, "POST", {"content": msg_content})
            
            if code in [200, 201]:
                self._json(200, {"status": "deployed"})
            else:
                self._json(200, {"status": "failed", "discord_error_code": code, "error": str(res_body)})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _json(self, code, data):
        self.send_response(code); self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*'); self.end_headers()
        self.wfile.write(json.dumps(data).encode())
