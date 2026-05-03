from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
from curl_cffi import requests

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()

    def handle_request(self):
        # 1. Parse parameters
        parsed_path = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_path.query)
        
        target_url = query.get('target', [''])[0]
        
        if not target_url:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing target URL"}).encode('utf-8'))
            return

        # 2. Execute TLS Spoofed Request
        try:
            # We spoof Chrome 120 to bypass Cloudflare TLS fingerprinting
            response = requests.get(
                target_url, 
                impersonate="chrome120",
                timeout=8 # Vercel timeout is 10s, fail fast
            )
            
            # 3. Analyze the result
            status_code = response.status_code
            html_content = response.text
            
            # Check for Cloudflare blocks
            is_cf_blocked = False
            if status_code in [403, 503] or "cloudflare" in html_content.lower() or "just a moment" in html_content.lower():
                is_cf_blocked = True

            result = {
                "success": True,
                "target": target_url,
                "status_code": status_code,
                "cloudflare_blocked": is_cf_blocked,
                "content_length": len(html_content),
                "title": self.extract_title(html_content)
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

    def extract_title(self, html):
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.title.string if soup.title else "No Title Found"
            return title.strip()
        except Exception:
            return "Parsing Error"
