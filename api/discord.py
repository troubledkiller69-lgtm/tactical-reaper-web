from http.server import BaseHTTPRequestHandler
import json
import os
import uuid
import urllib.request
import urllib.parse
from discord_interactions import verify_key

# BIFROST DISCORD-BRIDGE INTERACTION API (v16.1)
# No Supabase. Everything is handled via the Auth Channel.

DISCORD_PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
AUTH_CHANNEL_ID = os.getenv("AUTH_CHANNEL_ID")

def post_key_to_discord(key, operator):
    """Posts the generated key to the Auth Channel for persistence."""
    if not DISCORD_TOKEN or not AUTH_CHANNEL_ID:
        return False
    
    url = f"https://discord.com/api/v10/channels/{AUTH_CHANNEL_ID}/messages"
    payload = json.dumps({"content": f"KEY: {key} | OP: {operator}"}).encode('utf-8')
    
    req = urllib.request.Request(url, data=payload, method='POST')
    req.add_header('Authorization', f'Bot {DISCORD_TOKEN}')
    req.add_header('Content-Type', 'application/json')
    
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.getcode() == 200
    except:
        return False

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. Verify Signature
        signature = self.headers.get("X-Signature-Ed25519")
        timestamp = self.headers.get("X-Signature-Timestamp")
        
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        try:
            if not DISCORD_PUBLIC_KEY or not verify_key(raw_body, signature, timestamp, DISCORD_PUBLIC_KEY):
                self.send_response(401)
                self.end_headers()
                return
        except:
            self.send_response(401)
            self.end_headers()
            return

        # 2. Parse Body
        body = json.loads(raw_body.decode('utf-8'))

        # 3. Handle Ping
        if body.get("type") == 1:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"type": 1}).encode('utf-8'))
            return

        # 4. Handle Commands
        if body.get("type") == 2:
            data = body.get("data", {})
            command_name = data.get("name")

            if command_name == "genkey":
                operator = "CLEAN"
                for opt in data.get("options", []):
                    if opt["name"] == "operator_id": operator = opt["value"]

                # Generate
                new_key = f"Retri-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"
                
                # Sync to Auth Channel
                success = post_key_to_discord(new_key, operator)
                
                if success:
                    content = f"🚀 **BIFROST LICENSE ACTIVATED**\n\n**KEY:** `{new_key}`\n**OP:** `{operator}`\n\n*License synchronized to vault.*"
                else:
                    content = f"❌ **ERROR:** COULD NOT SYNC TO VAULT (Check AUTH_CHANNEL_ID)"

                reply = {"type": 4, "data": {"content": content}}
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(reply).encode('utf-8'))
                return

        self.send_response(400)
        self.end_headers()
