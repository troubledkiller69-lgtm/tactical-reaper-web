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
        # Using proxyscrape as a reliable free source for raw proxies
        url = f"https://api.proxyscrape.com/v2/?request=displayproxies&protocol={protocol}&timeout=10000&country=all&ssl=all&anonymity=all"
        
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                # Raw list of proxies from the API
                raw_proxies = [p.strip() for p in r.text.split('\n') if p.strip()]
                
                # We won't test them all here because serverless timeouts (10s limit).
                # We will return the top 100 raw proxies to the client.
                # In a real environment, the client would test them locally or we'd use a background queue.
                
                proxies_to_return = raw_proxies[:100]
                
                self._json(200, {
                    "status": "success",
                    "protocol": protocol,
                    "count": len(proxies_to_return),
                    "proxies": proxies_to_return,
                    "note": "Proxies are raw and unverified. Some may be dead."
                })
            else:
                self._json(500, {"error": "Failed to fetch from proxy provider"})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_POST(self):
        self.do_GET()
