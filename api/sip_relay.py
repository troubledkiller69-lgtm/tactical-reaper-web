import asyncio
import aiohttp
import json
import os
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
            action = data.get('action', '')
            
            if action == 'initiate':
                # Artery Bridge v1.1 - Live Zadarma Signaling
                import hashlib
                import requests
                
                z_key = data.get('sip_user').split('-')[0] # Usually the first part
                z_secret = data.get('sip_pass')
                target = data.get('target')
                cid = data.get('cid') or "BIFROST"
                
                method = "/v1/request/callback/"
                params = {"from": cid, "to": target}
                sorted_params = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
                
                md5_params = hashlib.md5(sorted_params.encode()).hexdigest()
                data_to_sign = f"{method}{sorted_params}{md5_params}"
                signature = hashlib.md5((data_to_sign + z_secret).encode()).hexdigest()
                
                auth_header = f"{z_key}:{signature}"
                
                # Fire the actual API call to Zadarma
                r = requests.get(f"https://api.zadarma.com{method}", params=params, headers={"Authorization": auth_header})
                res_data = r.json()
                
                if r.status_code == 200 and res_data.get('status') == 'success':
                    self._json(200, {
                        "status": "dialing",
                        "info": "Signal dispatched to Zadarma Backbone",
                        "provider": "Zadarma (Artery)"
                    })
                else:
                    self._json(r.status_code, {"error": res_data.get('message') or "Zadarma Auth Failure"})
            else:
                self._json(400, {"error": "Invalid action"})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
