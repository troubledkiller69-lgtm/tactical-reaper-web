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
        
        try:
            # 1. Handle Login if credentials provided
            if action == "login" or (username and password):
                login_result = self.perform_login(session, target_url, username, password)
                if not login_result["success"]:
                    self.send_response_json(login_result)
                    return

            # 2. Execute Snipe
            response = session.get(
                target_url if action != "login" else f"{target_url}/inventory", 
                impersonate="chrome120",
                timeout=10
            )
            
            status_code = response.status_code
            html_content = response.text
            
            is_cf_blocked = False
            if status_code in [403, 503] or "cloudflare" in html_content.lower():
                is_cf_blocked = True

            # 3. Scrape Assets (Placeholder for actual table parsing)
            assets = self.parse_assets(html_content, query.get('filter', [''])[0])

            result = {
                "success": True,
                "target": target_url,
                "status_code": status_code,
                "cloudflare_blocked": is_cf_blocked,
                "title": self.extract_title(html_content),
                "assets_found": len(assets),
                "assets": assets[:5] # Return first 5 matches
            }
            
            self.send_response_json(result)
            
        except Exception as e:
            self.send_error_json(str(e))

    def perform_login(self, session, base_url, user, pw):
        # Most Russian shops use /login or /auth/login
        login_url = f"{base_url.rstrip('/')}/login"
        payload = {
            "username": user,
            "password": pw,
            "login": "submit" # Common button name
        }
        
        try:
            resp = session.post(login_url, data=payload, impersonate="chrome120", timeout=10)
            if resp.status_code == 200 and ("logout" in resp.text.lower() or "profile" in resp.text.lower()):
                return {"success": True, "msg": "Login Successful"}
            return {"success": False, "msg": f"Login Failed (Status {resp.status_code})", "debug": resp.text[:200]}
        except Exception as e:
            return {"success": False, "msg": f"Login Error: {str(e)}"}

    def parse_assets(self, html, filter_text):
        # Basic keyword search in HTML tables for now
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        matches = []
        
        # Look for table rows that might contain CC data
        for row in soup.find_all('tr'):
            text = row.get_text().upper()
            if filter_text.upper() in text:
                matches.append(text.strip().replace('\n', ' | '))
        
        return matches

    def send_response_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_error_json(self, msg):
        self.send_response(200) # Keep 200 for frontend to handle data.error
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"error": msg, "success": False}).encode('utf-8'))

    def extract_title(self, html):
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            return soup.title.string.strip() if soup.title else "No Title"
        except: return "Parsing Error"
