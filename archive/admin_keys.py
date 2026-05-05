import os
import json
import requests
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# BIFROST ADMIN KEY MANAGER (v18.1)
# Securely generates and manages keys via Discord Vault.

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
AUTH_CHANNEL_ID = os.getenv("AUTH_CHANNEL_ID")
ADMIN_KEY = os.getenv("ADMIN_KEY")

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Key')
        self.end_headers()

    def do_GET(self):
        # Security Check: Verify Admin Key in Headers
        auth_key = self.headers.get('X-Admin-Key')
        if not auth_key or auth_key != ADMIN_KEY:
            self._error_response("UNAUTHORIZED", 401)
            return

        if not DISCORD_TOKEN or not AUTH_CHANNEL_ID:
            self._error_response("INFRASTRUCTURE_ERROR: DISCORD_CONFIG_MISSING", 500)
            return

        url = f"https://discord.com/api/v10/channels/{AUTH_CHANNEL_ID}/messages?limit=100"
        headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                messages = response.json()
                keys = []
                for msg in messages:
                    content = msg.get("content", "")
                    if "KEY:" in content:
                        keys.append({
                            "content": content,
                            "timestamp": msg.get("timestamp"),
                            "id": msg.get("id")
                        })
                self._success_response({"keys": keys})
            else:
                self._error_response(f"DISCORD_API_ERROR: {response.status_code}", response.status_code)
        except Exception as e:
            self._error_response(str(e), 500)

    def do_POST(self):
        # Security Check: Verify Admin Key in Headers
        auth_key = self.headers.get('X-Admin-Key')
        if not auth_key or auth_key != ADMIN_KEY:
            self._error_response("UNAUTHORIZED", 401)
            return

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = json.loads(self.rfile.read(content_length))
        
        new_key = post_data.get('key')
        operator = post_data.get('operator', 'OPERATOR')
        
        if not new_key:
            self._error_response("MISSING_KEY_DATA", 400)
            return

        discord_content = f"KEY: {new_key} | OP: {operator}"
        url = f"https://discord.com/api/v10/channels/{AUTH_CHANNEL_ID}/messages"
        headers = {
            "Authorization": f"Bot {DISCORD_TOKEN}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, headers=headers, json={"content": discord_content})
            if response.status_code == 200 or response.status_code == 201:
                self._success_response({"status": "deployed", "key": new_key})
            else:
                self._error_response(f"DISCORD_API_ERROR: {response.status_code}", response.status_code)
        except Exception as e:
            self._error_response(str(e), 500)

    def _success_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _error_response(self, message, code):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode())
