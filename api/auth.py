import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# BIFROST SECURE AUTH ENGINE (v18.3)
# Zero-dependency implementation for maximum reliability.

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
AUTH_CHANNEL_ID = os.getenv("AUTH_CHANNEL_ID")
ADMIN_KEY = os.getenv("ADMIN_KEY")
ADMIN_OPERATOR = os.getenv("ADMIN_OPERATOR", "ADMIN")

def discord_request(url, method="GET", body=None):
    if not DISCORD_TOKEN: return None
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bot {DISCORD_TOKEN}")
    req.add_header("Content-Type", "application/json")
    try:
        data = json.dumps(body).encode() if body else None
        with urllib.request.urlopen(req, data=data, timeout=10) as res:
            return res.getcode(), json.loads(res.read().decode())
    except Exception as e:
        print(f"Discord API Error: {e}")
        return 500, None

def fetch_keys():
    if not AUTH_CHANNEL_ID: return {}, []
    url = f"https://discord.com/api/v10/channels/{AUTH_CHANNEL_ID}/messages?limit=50"
    code, messages = discord_request(url)
    keys = {}
    raw = []
    if code == 200 and messages:
        for msg in messages:
            content = msg.get("content", "")
            raw.append({"content": content, "timestamp": msg.get("timestamp"), "id": msg.get("id")})
            if "KEY:" in content:
                try:
                    parts = content.split("|")
                    k = parts[0].replace("KEY:", "").strip()
                    op = parts[1].replace("OP:", "").strip() if len(parts) > 1 else "OPERATOR"
                    keys[k] = {"operator_id": op, "status": "active"}
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
        key_input = query.get('pass', [None])[0]
        
        if action == 'verify':
            if ADMIN_KEY and key_input == ADMIN_KEY:
                self._json(200, {"status": "success", "data": {"operator_id": ADMIN_OPERATOR, "role": "commander"}})
            else:
                keys, _ = fetch_keys()
                if key_input in keys:
                    self._json(200, {"status": "success", "data": keys[key_input]})
                else:
                    self._json(400, {"status": "error", "message": "INVALID_KEY"})

        elif action == 'list':
            if self.headers.get('X-Admin-Key') == ADMIN_KEY:
                _, raw = fetch_keys()
                self._json(200, {"keys": raw})
            else:
                self._json(401, {"error": "UNAUTHORIZED"})

    def do_POST(self):
        if self.headers.get('X-Admin-Key') != ADMIN_KEY:
            self._json(401, {"error": "UNAUTHORIZED"}); return

        try:
            cl = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(cl))
            new_key, op = body.get('key'), body.get('operator', 'OPERATOR')
            if not new_key: self._json(400, {"error": "MISSING_KEY"}); return

            url = f"https://discord.com/api/v10/channels/{AUTH_CHANNEL_ID}/messages"
            code, _ = discord_request(url, "POST", {"content": f"KEY: {new_key} | OP: {op}"})
            self._json(200, {"status": "deployed" if code in [200, 201] else "failed"})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _json(self, code, data):
        self.send_response(code); self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*'); self.end_headers()
        self.wfile.write(json.dumps(data).encode())
