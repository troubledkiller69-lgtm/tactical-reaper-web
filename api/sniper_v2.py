from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import requests

HF_UPLINK = "https://rxtri-bifrost.hf.space/api/sniper"

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

        # 2. Proxy to HuggingFace Bypass Engine
        try:
            params = {
                "target": target_url,
                "user": username,
                "pass": password
            }
            # We hit our own HF space which has curl_cffi installed
            resp = requests.get(HF_UPLINK, params=params, timeout=20)
            result = resp.json()
        except Exception as e:
            result = {"error": f"UPLINK_FAILED: {str(e)}", "success": False}

        # 3. Respond
        self.send_response_json(result)

    def do_POST(self):
        self.do_GET()

    def send_response_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
