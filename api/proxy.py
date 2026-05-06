import json
import urllib.parse
from http.server import BaseHTTPRequestHandler
import requests
import concurrent.futures

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        action = query.get('action', ['harvest'])[0]
        protocol = query.get('protocol', ['socks5'])[0] # http, socks4, socks5, all
        
        if action == 'harvest':
            self.harvest_proxies(protocol)
        else:
            self._json(400, {"error": "Invalid action"})

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

    def do_POST(self):
        self.do_GET()
