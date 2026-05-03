import asyncio
import json
import maigret
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        username = query.get('username', [None])[0]

        if not username:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing username")
            return

        # Setup Maigret
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            db = maigret.MaigretDatabase().load_from_file('./maigret/resources/data.json')
            # Limit to top sites to avoid timeout
            sites = db.sites[:50] 
            
            searcher = maigret.MaigretSearcher(
                username=username,
                sites=sites,
                timeout=10,
                no_check_certificate=True
            )
            
            results = loop.run_until_complete(searcher.search())
            
            found = []
            for site_name, result in results.items():
                if result['status'] == maigret.MaigretCheckStatus.CLAIMED:
                    found.append({
                        'site': site_name,
                        'url': result['url_user']
                    })

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'success',
                'username': username,
                'matches': found
            }).encode())

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())
        finally:
            loop.close()
