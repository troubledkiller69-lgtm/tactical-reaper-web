from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import os

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://smxpzldbxewcgrakaqhn.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_QviDYLWIVjVJl4N01Bqaug_ZgkNHcde")

def get_active_keys_count():
    try:
        url = f"{SUPABASE_URL}/rest/v1/keys?status=eq.active&select=id"
        req = urllib.request.Request(url, method='GET')
        req.add_header('apikey', SUPABASE_KEY)
        req.add_header('Authorization', f'Bearer {SUPABASE_KEY}')
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return len(data)
    except Exception as e:
        print("Stats fetch error:", e)
        return 0  # Fallback if table doesn't exist or auth fails

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.end_headers()

    def do_GET(self):
        try:
            active_keys = get_active_keys_count()
            
            data = {
                "active_keys": active_keys,
                "revenue": 0
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
