from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import requests

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self.execute_sniper_logic()
        except Exception as e:
            self.send_error_json(f"ENGINE_CRASH: {str(e)}")

    def do_POST(self):
        try:
            self.execute_sniper_logic()
        except Exception as e:
            self.send_error_json(f"ENGINE_CRASH: {str(e)}")

    def execute_sniper_logic(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_path.query)
        
        target_url = query.get('target', [''])[0]
        action = query.get('action', ['snipe'])[0]
        username = query.get('user', [''])[0]
        password = query.get('pass', [''])[0]
        
        if not target_url:
            self.send_error_json("Missing target URL")
            return

        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        
        try:
            # 1. Handle Login
            if username and password:
                login_url = f"{target_url.rstrip('/')}/login"
                try:
                    session.post(login_url, data={"username": username, "password": password, "login": "submit"}, timeout=5)
                except: pass

            # 2. Execute Snipe
            resp = session.get(target_url, timeout=10)
            
            result = {
                "success": True,
                "status_code": resp.status_code,
                "cloudflare_blocked": "cloudflare" in resp.text.lower() or resp.status_code in [403, 503],
                "title": "BIFROST Target"
            }
            
            self.send_response_json(result)
            
        except Exception as e:
            self.send_error_json(str(e))

    def send_response_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_error_json(self, msg):
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": msg, "success": False}).encode('utf-8'))
        except:
            pass
