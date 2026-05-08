import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# BIFROST LOCAL IDENTITY VAULT (v15.0)
# This replaces the unreliable Supabase backend with a repository-anchored key system.
# TO ADD KEYS: Update the VALID_KEYS dictionary below.

VALID_KEYS = {
    "Retri-9798B3D2-0B248109": {"operator_id": "Clean", "status": "active"}
}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        key_input = query.get('pass', [None])[0]
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        if key_input in VALID_KEYS:
            result = {
                "status": "success",
                "data": VALID_KEYS[key_input]
            }
        else:
            result = {
                "status": "error",
                "message": "INVALID KEY"
            }
            
        self.wfile.write(json.dumps(result).encode())
