import json
import base64
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from ghunt.models import GHuntCreds
from ghunt.objects import GAccount
from ghunt.helpers.auth import check_and_gen_creds

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)
        
        email = data.get('email')
        cookies_b64 = data.get('cookies_b64')

        if not email or not cookies_b64:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Missing email or cookies_b64'}).encode())
            return

        try:
            # Decode cookies
            cookies_json = base64.b64decode(cookies_b64).decode()
            creds = GHuntCreds(cookies_json)
            
            # Investigate email
            ga = GAccount(email)
            # This is a simplified version, real GHunt 2.0 requires async and more complex setup
            # but for a proof of concept on Vercel:
            
            # In a real scenario, we'd use GHunt's modules to fetch info
            # Here we simulate the response for the UI integration
            
            result = {
                'status': 'success',
                'email': email,
                'profile': {
                    'name': 'BIFROST OPERATOR',
                    'gaia_id': '123456789',
                    'last_updated': '2026-05-03',
                    'services': ['YouTube', 'Maps', 'Photos']
                }
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
