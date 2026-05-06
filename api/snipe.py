from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import traceback
import requests

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self.handle_request()
        except Exception as e:
            self.send_error_json(f"ENGINE_CRASH: {str(e)}")

    def do_POST(self):
        try:
            self.handle_request()
        except Exception as e:
            self.send_error_json(f"ENGINE_CRASH: {str(e)}")

    def handle_request(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_path.query)
        
        target_url = query.get('target', [''])[0]
        action = query.get('action', ['snipe'])[0]
        username = query.get('user', [''])[0]
        password = query.get('pass', [''])[0]
        filter_text = query.get('filter', [''])[0]
        
        if not target_url:
            self.send_error_json("Missing target URL")
            return

        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        })
        
        try:
            # 1. Handle Login
            if username and password:
                login_url = f"{target_url.rstrip('/')}/login"
                session.post(login_url, data={"username": username, "password": password, "login": "submit"}, timeout=10)

            # 2. Execute Snipe
            resp = session.get(target_url, timeout=10)
            
            # 3. Parse and Respond
            result = {
                "success": True,
                "status_code": resp.status_code,
                "cloudflare_blocked": "cloudflare" in resp.text.lower() or resp.status_code in [403, 503],
                "content_length": len(resp.text),
                "title": "Ultimateshop" if "ultimateshop" in target_url else "Target Endpoint"
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
            
        except Exception as e:
            self.send_error_json(f"REQUEST_FAILED: {str(e)}")

    def send_error_json(self, msg):
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": msg, "success": False}).encode('utf-8'))
        except:
            pass # Prevent recursion if send_response fails
