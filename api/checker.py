import json
import asyncio
import aiohttp
import urllib.parse
from http.server import BaseHTTPRequestHandler
import time

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
            action = data.get('action', 'check')
            
            if action == 'check':
                combo = data.get('combo', []) # Format: email:pass
                target = data.get('target', 'netflix') # netflix, hulu, disney, etc.
                proxies = data.get('proxies', [])
                
                results = asyncio.run(self.run_check(combo, target, proxies))
                self._json(200, {
                    "status": "success",
                    "total": len(combo),
                    "results": results
                })
            else:
                self._json(400, {"error": "Invalid action"})
        except Exception as e:
            self._json(400, {"error": str(e)})

    async def check_account(self, session, email, password, target, proxy):
        # This is a placeholder for target-specific logic
        # In a real scenario, you'd have different request flows for each target
        await asyncio.sleep(0.5) # Simulate request
        import random
        status = random.choice(["Hit", "Bad", "2FA", "Expired"])
        
        return {
            "account": f"{email}:{password}",
            "status": status,
            "target": target,
            "info": "Captured via BIFROST Shadow Engine" if status == "Hit" else "N/A"
        }

    async def run_check(self, combo, target, proxies):
        connector = aiohttp.TCPConnector(limit=50)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for i, line in enumerate(combo):
                if ':' not in line: continue
                email, password = line.split(':', 1)
                proxy = proxies[i % len(proxies)] if proxies else None
                tasks.append(self.check_account(session, email, password, target, proxy))
            
            return await asyncio.gather(*tasks)

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
