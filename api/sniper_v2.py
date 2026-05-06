from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import requests

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Parse Query
        parsed_path = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_path.query)
        target_url = query.get('target', [''])[0]
        username = query.get('user', [''])[0]
        password = query.get('pass', [''])[0]
        
        if not target_url:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing target URL"}).encode())
            return

        # 2. Execute Request
        try:
            session = requests.Session()
            session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
            
            if username and password:
                try:
                    session.post(f"{target_url.rstrip('/')}/login", data={"username": username, "password": password, "login": "submit"}, timeout=5)
                except: pass

            resp = session.get(target_url, timeout=10)
            result = {
                "success": True,
                "status_code": resp.status_code,
                "cloudflare_blocked": "cloudflare" in resp.text.lower() or resp.status_code in [403, 503],
                "title": "BIFROST Target"
            }
        except Exception as e:
            result = {"error": str(e), "success": False}

        # 3. Respond
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode('utf-8'))

    def do_POST(self):
        self.do_GET()
