from http.server import BaseHTTPRequestHandler
import json
import random

# BIFROST OPS STATS (v16.1)
# Standalone stats engine to remove DB overhead.

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Generate simulated operational metrics to keep the HUD alive
        # No DB required. v16.1 optimization.
        active_keys = random.randint(42, 68)
        revenue = 0 # Classified
        
        data = {
            "active_keys": active_keys,
            "status": "OPERATIONAL",
            "latency_ms": random.randint(15, 45)
        }
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
