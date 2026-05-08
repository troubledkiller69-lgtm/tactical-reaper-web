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
        # Protocols mapping
        ps_proto = protocol if protocol != 'all' else 'socks5'
        geo_proto = protocol if protocol != 'all' else 'socks5'
        
        # Sources refined for US-primary freshness
        sources = [
            # Source 1: ProxyScrape (Targeting US)
            f"https://api.proxyscrape.com/v2/?request=displayproxies&protocol={ps_proto}&timeout=10000&country=US&ssl=all&anonymity=all",
            # Source 2: Geonode (Targeting US, sorted by lastChecked)
            f"https://proxylist.geonode.com/api/proxy-list?limit=100&page=1&sort_by=lastChecked&sort_type=desc&protocols={geo_proto}&country=US",
            # Source 3: Spys.me (Daily list)
            "https://spys.me/socks.txt" if ps_proto == 'socks5' else "https://spys.me/proxy.txt",
            # Source 4: Monosans (High quality GitHub repo)
            f"https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/{"socks5" if ps_proto == 'socks5' else "http"}.txt",
            # Source 5: Proxy-List.download
            f"https://www.proxy-list.download/api/v1/get?type={ps_proto}&country=US"
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
                                    proxies.add(f"{parts[0]}:{parts[1]}")
            except: pass

        results = list(proxies)[:500] # Increased limit to 500 for better selection
        
        self._json(200, {
            "status": "success",
            "protocol": protocol,
            "country": "US",
            "count": len(results),
            "proxies": results,
            "note": "Optimized for fresh US nodes from Spys.me, Geonode, and Monosans."
        })

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
