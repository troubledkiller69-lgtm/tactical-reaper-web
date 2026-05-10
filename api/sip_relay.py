import json
import urllib.request
from http.server import BaseHTTPRequestHandler

# The IP of our new Asterisk VPS Bridge
VPS_BRIDGE_URL = "http://144.172.100.234:8080"

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
            action = data.get('action', '')
            
            if action == 'initiate':
                # BIFROST Artery v2.0 - VPS Bridge Relay
                target = data.get('target')
                cid = data.get('cid', '0000000000')
                prompt = data.get('prompt', '')
                voice_id = data.get('voice_id', '21m00Tcm4TlvDq8ikWAM')

                if not target:
                    return self._json(400, {"error": "Target required"})

                payload = json.dumps({
                    "target": target,
                    "cid": cid,
                    "prompt": prompt,
                    "voice_id": voice_id
                }).encode('utf-8')

                req = urllib.request.Request(f"{VPS_BRIDGE_URL}/call", data=payload, headers={'Content-Type': 'application/json'})
                
                try:
                    with urllib.request.urlopen(req, timeout=10) as response:
                        res_data = json.loads(response.read().decode())
                        self._json(200, res_data)
                except Exception as e:
                    self._json(500, {"error": f"VPS Bridge Unreachable: {str(e)}"})

            elif action == 'latest_otp':
                # Poll the VPS for the latest captured digits
                try:
                    with urllib.request.urlopen(f"{VPS_BRIDGE_URL}/otp", timeout=5) as response:
                        res_data = json.loads(response.read().decode())
                        self._json(200, res_data)
                except Exception as e:
                    self._json(500, {"error": "Failed to poll OTP"})
                    
            else:
                self._json(400, {"error": "Invalid action"})
                
        except Exception as e:
            self._json(500, {"error": str(e)})

    def do_GET(self):
        # Health check
        self._json(200, {"status": "Artery Bridge Proxy Online"})

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
