import asyncio
import json
import aiohttp
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

        # Lightweight Maigret-style search (Ghost-Lite Engine)
        sites = [
            {"name": "GitHub", "url": "https://github.com/{}"},
            {"name": "Twitter", "url": "https://twitter.com/{}"},
            {"name": "Instagram", "url": "https://instagram.com/{}"},
            {"name": "Reddit", "url": "https://reddit.com/user/{}"},
            {"name": "YouTube", "url": "https://youtube.com/@{}"},
            {"name": "Pinterest", "url": "https://pinterest.com/{}"},
            {"name": "Telegram", "url": "https://t.me/{}"},
            {"name": "Snapchat", "url": "https://snapchat.com/add/{}"},
            {"name": "TikTok", "url": "https://tiktok.com/@{}"},
            {"name": "Steam", "url": "https://steamcommunity.com/id/{}"},
            {"name": "Twitch", "url": "https://twitch.tv/{}"},
            {"name": "SoundCloud", "url": "https://soundcloud.com/{}"},
            {"name": "Vimeo", "url": "https://vimeo.com/{}"},
            {"name": "Behance", "url": "https://behance.net/{}"},
            {"name": "Medium", "url": "https://medium.com/@{}"}
        ]

        async def check_site(session, site, username):
            url = site["url"].format(username)
            try:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        return {"site": site["name"], "url": url}
            except:
                pass
            return None

        async def run_search():
            async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
                tasks = [check_site(session, site, username) for site in sites]
                results = await asyncio.gather(*tasks)
                return [r for r in results if r]

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        found = loop.run_until_complete(run_search())
        loop.close()

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "success",
            "username": username,
            "matches": found
        }).encode())
