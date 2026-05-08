import json
import requests
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # We'll use Etherscan/BscScan APIs for live tracking
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        action = query.get('action', ['track'])[0]
        address = query.get('address', [''])[0]
        chain = query.get('chain', ['eth'])[0]
        
        if action == 'balance':
            self.get_balance(address, chain)
        elif action == 'history':
            self.get_history(address, chain)
        else:
            self._json(400, {"error": "Invalid action"})

    def get_balance(self, address, chain):
        # Placeholder for API calls
        # In a real scenario, use Etherscan API key from .env
        self._json(200, {
            "address": address,
            "chain": chain,
            "balance": "0.42",
            "symbol": chain.upper()
        })

    def get_history(self, address, chain):
        self._json(200, {
            "address": address,
            "chain": chain,
            "transactions": [
                {"hash": "0xabc...", "value": "1.5", "type": "IN"},
                {"hash": "0xdef...", "value": "0.2", "type": "OUT"}
            ]
        })

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
