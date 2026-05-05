import os
import json
import requests
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# BIFROST UNIFIED AUTH & ADMIN (v18.2)
# Consolidates auth_vault and admin_keys to save Vercel serverless slots.

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
AUTH_CHANNEL_ID = os.getenv("AUTH_CHANNEL_ID")
ADMIN_KEY = os.getenv("ADMIN_KEY")
ADMIN_OPERATOR = os.getenv("ADMIN_OPERATOR", "ADMIN")

def fetch_discord_keys():
    if not DISCORD_TOKEN or not AUTH_CHANNEL_ID: return {}
    url = f"https://discord.com/api/v10/channels/{AUTH_CHANNEL_ID}/messages?limit=100"
    headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            messages = response.json()
            keys = {}
            raw_messages = []
            for msg in messages:
                content = msg.get("content", "")
                raw_messages.append({"content": content, "timestamp": msg.get("timestamp"), "id": msg.get("id")})
                if "KEY:" in content:
                    try:
                        parts = content.split("|")
                        key_part = parts[0].replace("KEY:", "").strip()
                        op_part = parts[1].replace("OP:", "").strip() if len(parts) > 1 else "OPERATOR"
                        keys[key_part] = {"operator_id": op_part, "status": "active"}
                    except: continue
            return keys, raw_messages
    except: pass
    return {}, []

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
        
        # Action: Verify (Standard Login)
        if action == 'verify':
            if ADMIN_KEY and key_input == ADMIN_KEY:
                self._json(200, {"status": "success", "data": {"operator_id": ADMIN_OPERATOR, "status": "active", "role": "commander"}})
            else:
                keys, _ = fetch_discord_keys()
                if key_input in keys:
                    self._json(200, {"status": "success", "data": keys[key_input]})
                else:
                    self._json(400, {"status": "error", "message": "INVALID_OR_EXPIRED_LICENSE"})

        # Action: List (Admin Only)
        elif action == 'list':
            auth_key = self.headers.get('X-Admin-Key')
            if auth_key == ADMIN_KEY:
                _, raw = fetch_discord_keys()
                self._json(200, {"keys": raw})
            else:
                self._json(401, {"error": "UNAUTHORIZED"})

    def do_POST(self):
        # Action: Deploy (Admin Only)
        auth_key = self.headers.get('X-Admin-Key')
        if not auth_key or auth_key != ADMIN_KEY:
            self._json(401, {"error": "UNAUTHORIZED"})
            return

        try:
            cl = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(cl))
            new_key = body.get('key')
            operator = body.get('operator', 'OPERATOR')
            
            if not new_key:
                self._json(400, {"error": "MISSING_KEY"})
                return

            msg = f"KEY: {new_key} | OP: {operator}"
            url = f"https://discord.com/api/v10/channels/{AUTH_CHANNEL_ID}/messages"
            headers = {"Authorization": f"Bot {DISCORD_TOKEN}", "Content-Type": "application/json"}
            res = requests.post(url, headers=headers, json={"content": msg})
            if res.status_code in [200, 201]:
                self._json(200, {"status": "deployed", "key": new_key})
            else:
                self._json(res.status_code, {"error": f"DISCORD_ERR: {res.status_code}"})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
