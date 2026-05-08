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
        # Protocols mapping for different APIs
        ps_proto = protocol if protocol != 'all' else 'socks5'
        geo_proto = protocol if protocol != 'all' else 'socks5'
        
        # Source 1: ProxyScrape
        url1 = f"https://api.proxyscrape.com/v2/?request=displayproxies&protocol={ps_proto}&timeout=10000&country=all&ssl=all&anonymity=all"
        
        # Source 2: Geonode (Free List API)
        url2 = f"https://proxylist.geonode.com/api/proxy-list?limit=100&page=1&sort_by=lastChecked&sort_type=desc&protocols={geo_proto}"

        proxies = set()
        
        # Fetch from ProxyScrape
        try:
            r1 = requests.get(url1, timeout=5)
            if r1.status_code == 200:
                for p in r1.text.split('\n'):
                    if p.strip(): proxies.add(p.strip())
        except: pass

        # Fetch from Geonode
        try:
            r2 = requests.get(url2, timeout=5)
            if r2.status_code == 200:
                data = r2.json().get('data', [])
                for item in data:
                    proxies.add(f"{item['ip']}:{item['port']}")
        except: pass

        results = list(proxies)[:250] # Limit to 250 for response size/speed
        
        self._json(200, {
            "status": "success",
            "protocol": protocol,
            "count": len(results),
            "proxies": results,
            "note": "Combined results from multiple upstream providers. Unverified."
        })

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
