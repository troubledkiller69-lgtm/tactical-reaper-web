from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import httpx

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Parse Query
        parsed_path = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_path.query)
        target_url = query.get('target', [''])[0]
        username = query.get('user', [''])[0]
        password = query.get('pass', [''])[0]
        
        if not target_url:
            self.send_response_json({"error": "Missing target URL", "success": False})
            return

        # 2. Advanced HTTP/2 Impersonation
        try:
            # We use HTTP/2 which is a key bypass for many Cloudflare rules
            client = httpx.Client(http2=True, timeout=15.0)
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1"
            }
            
            # Prime the session
            try:
                client.get(target_url, headers=headers)
            except: pass

            # 3. Handle Login
            if username and password:
                login_url = f"{target_url.rstrip('/')}/login"
                login_headers = headers.copy()
                login_headers.update({"Referer": target_url, "Origin": target_url, "Sec-Fetch-Site": "same-origin"})
                try:
                    client.post(login_url, data={"username": username, "password": password, "login": "submit"}, headers=login_headers)
                except: pass

            # 4. Execute Snipe
            resp = client.get(target_url, headers=headers)
            
            result = {
                "success": True,
                "status_code": resp.status_code,
                "cloudflare_blocked": "cloudflare" in resp.text.lower() or resp.status_code in [403, 503],
                "content_length": len(resp.text),
                "title": "BIFROST Target"
            }
            
            self.send_response_json(result)
            
        except Exception as e:
            self.send_response_json({"error": str(e), "success": False})

    def do_POST(self):
        self.do_GET()

    def send_response_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
