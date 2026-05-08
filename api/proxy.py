import json
import urllib.parse
from http.server import BaseHTTPRequestHandler
import requests
import asyncio
import time
import random
from api.proxy_check import AsyncProxyChecker

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        action = query.get('action', ['harvest'])[0]
        protocol = query.get('protocol', ['socks5'])[0]
        
        if action == 'harvest':
            proxies = asyncio.run(self.harvest_proxies_async(protocol))
            self._json(200, {
                "status": "success",
                "protocol": protocol,
                "country": "US",
                "count": len(proxies),
                "proxies": proxies,
                "note": "STRICT US-ONLY ENFORCEMENT: Verified via async backend geo-validation."
            })
        elif action == 'check':
            proxies = query.get('proxies', [])
            if not proxies and 'list' in query:
                proxies = query['list'][0].split(',')
            self.check_proxies(proxies)
        else:
            self._json(400, {"error": "Invalid action"})

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
            action = data.get('action', 'check')
            if action == 'check':
                proxies = data.get('proxies', [])
                self.check_proxies(proxies)
            else:
                self._json(400, {"error": "Invalid action for POST"})
        except Exception as e:
            self._json(400, {"error": f"Invalid JSON: {str(e)}"})

    def check_proxies(self, proxies):
        if not proxies:
            self._json(400, {"error": "No proxies provided"})
            return
        checker = AsyncProxyChecker(proxies)
        results = asyncio.run(checker.run())
        live_count = len([r for r in results if r['status'] == 'Live'])
        self._json(200, {
            "status": "success",
            "total": len(results),
            "live": live_count,
            "results": results
        })

    async def batch_geo_filter_async(self, proxy_list):
        import aiohttp
        verified_us = []
        ips = [p.split(':')[0] for p in proxy_list]
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(0, len(ips), 15):
                batch = ips[i:i+15]
                tasks.append(session.post("http://ip-api.com/batch", json=batch, timeout=5))
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            for i, r in enumerate(responses):
                if isinstance(r, Exception): continue
                try:
                    if r.status == 200:
                        results = await r.json()
                        for idx, res in enumerate(results):
                            if res.get('countryCode') == 'US':
                                offset = i * 15
                                verified_us.append(proxy_list[offset + idx])
                except: pass
        return verified_us

    async def harvest_proxies_async(self, protocol):
        import aiohttp
        ps_proto = protocol if protocol != 'all' else 'socks5'
        geo_proto = protocol if protocol != 'all' else 'socks5'
        ts = int(time.time())
        sources = [
            f"https://api.proxyscrape.com/v2/?request=displayproxies&protocol={ps_proto}&timeout=10000&country=US&ssl=all&anonymity=all&_={ts}",
            f"https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols={geo_proto}&country=US&_={ts}",
            f"https://www.proxy-list.download/api/v1/get?type={ps_proto}&country=US&_={ts}",
            f"https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/us.txt?v={ts}",
            f"https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/countries/us/{"socks5" if ps_proto == 'socks5' else "http"}.txt?v={ts}",
            f"https://raw.githubusercontent.com/mmpx12/proxy-list/master/proxies/{"socks5" if ps_proto == 'socks5' else "http"}_us.txt?v={ts}" if ps_proto == 'socks5' else f"https://raw.githubusercontent.com/mmpx12/proxy-list/master/proxies/http_us.txt?v={ts}",
            f"https://raw.githubusercontent.com/Zaeem20/Free-Proxy-List/master/{"socks5" if ps_proto == 'socks5' else "http"}_us.txt?v={ts}",
            f"https://raw.githubusercontent.com/rdavydov/proxy-list/master/proxies/us.txt?v={ts}",
            f"https://raw.githubusercontent.com/UptimerBot/proxy-list/main/proxies/us.txt?v={ts}",
            f"https://raw.githubusercontent.com/officialputuid/free-proxy-list/master/proxies/countries/us.txt?v={ts}"
        ]
        raw_proxies = set()
        async with aiohttp.ClientSession() as session:
            tasks = [session.get(url, timeout=5) for url in sources]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            for i, r in enumerate(responses):
                if isinstance(r, Exception): continue
                try:
                    if r.status == 200:
                        url = sources[i]
                        if 'geonode' in url:
                            data = await r.json()
                            for item in data.get('data', []):
                                raw_proxies.add(f"{item['ip']}:{item['port']}")
                        else:
                            text = await r.text()
                            for p in text.split('\n'):
                                p = p.strip()
                                if p and ':' in p and not p.startswith('#'):
                                    parts = p.split(':')
                                    if len(parts) >= 2:
                                        raw_proxies.add(f"{parts[0].strip()}:{parts[1].strip()}")
                except: pass
        results = list(raw_proxies)
        random.shuffle(results)
        sample = results[:150]
        return await self.batch_geo_filter_async(sample)

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
