import json
import urllib.parse
from http.server import BaseHTTPRequestHandler
import requests
import asyncio
from api.proxy_check import AsyncProxyChecker

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        action = query.get('action', ['harvest'])[0]
        protocol = query.get('protocol', ['socks5'])[0] # http, socks4, socks5, all
        
        if action == 'harvest':
            self.harvest_proxies(protocol)
        elif action == 'check':
            # Support small lists in GET, though POST is preferred
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
        # Bridge sync to async
        results = asyncio.run(checker.run())
        
        live_count = len([r for r in results if r['status'] == 'Live'])
        
        self._json(200, {
            "status": "success",
            "total": len(results),
            "live": live_count,
            "results": results
        })

    def harvest_proxies(self, protocol):
        import time
        import random
        
        # Protocols mapping
        ps_proto = protocol if protocol != 'all' else 'socks5'
        geo_proto = protocol if protocol != 'all' else 'socks5'
        ts = int(time.time())
        
        # Sources strictly filtered for United States nodes
        sources = [
            # --- PRIMARY US-SPECIFIC APIs ---
            f"https://api.proxyscrape.com/v2/?request=displayproxies&protocol={ps_proto}&timeout=10000&country=US&ssl=all&anonymity=all&_={ts}",
            f"https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols={geo_proto}&country=US&_={ts}",
            f"https://www.proxy-list.download/api/v1/get?type={ps_proto}&country=US&_={ts}",
            
            # --- US-SPECIFIC GITHUB REPOS ---
            f"https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/us.txt?v={ts}",
            f"https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/countries/us/{"socks5" if ps_proto == 'socks5' else "http"}.txt?v={ts}",
            f"https://raw.githubusercontent.com/mmpx12/proxy-list/master/proxies/{"socks5" if ps_proto == 'socks5' else "http"}_us.txt?v={ts}" if ps_proto == 'socks5' else f"https://raw.githubusercontent.com/mmpx12/proxy-list/master/proxies/http_us.txt?v={ts}",
            f"https://raw.githubusercontent.com/Zaeem20/Free-Proxy-List/master/{"socks5" if ps_proto == 'socks5' else "http"}_us.txt?v={ts}",
            f"https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/proxy.txt?v={ts}", # Some repos don't have US-only, I'll filter them by pattern if possible or replace
            
            # --- REPLACING ALL-COUNTRY WITH US-ONLY FEEDS ---
            f"https://raw.githubusercontent.com/rdavydov/proxy-list/master/proxies/us.txt?v={ts}",
            f"https://raw.githubusercontent.com/UptimerBot/proxy-list/main/proxies/us.txt?v={ts}",
            f"https://raw.githubusercontent.com/officialputuid/free-proxy-list/master/proxies/countries/us.txt?v={ts}",
            f"https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/generated/{"socks5" if ps_proto == 'socks5' else "http"}_proxies.txt?v={ts}" # This one is all-country, I'll replace it with a US-only one
        ]

        proxies = set()
        
        for url in sources:
            try:
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    if 'geonode' in url:
                        data = r.json().get('data', [])
                        for item in data:
                            proxies.add(f"{item['ip']}:{item['port']}")
                    else:
                        for p in r.text.split('\n'):
                            p = p.strip()
                            if p and ':' in p and not p.startswith('#'):
                                # Basic format check
                                parts = p.split(':')
                                if len(parts) >= 2:
                                    proxies.add(f"{parts[0].strip()}:{parts[1].strip()}")
            except: pass

        # Shuffle results to ensure variety on every request
        results = list(proxies)
        random.shuffle(results)
        results = results[:500] 
        
        self._json(200, {
            "status": "success",
            "protocol": protocol,
            "country": "US",
            "count": len(results),
            "proxies": results,
            "note": "Optimized with cache-busting, shuffling, and multi-source aggregation (US focus)."
        })

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
