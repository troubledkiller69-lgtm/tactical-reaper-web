import os
import json
import requests
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# BIFROST DISCORD-SYNC AUTH (v16.0)
# This system uses a Discord channel as the database for keys.
# To manage keys: Simply post "KEY: Retri-XXXX | OP: Name" in the auth channel.

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
AUTH_CHANNEL_ID = os.getenv("AUTH_CHANNEL_ID")
ADMIN_KEY = os.getenv("ADMIN_KEY")
ADMIN_OPERATOR = os.getenv("ADMIN_OPERATOR", "ADMIN")

def fetch_discord_keys():
    """Fetches parseable keys from the designated Discord channel."""
    if not DISCORD_TOKEN or not AUTH_CHANNEL_ID:
        return {}
    
    url = f"https://discord.com/api/v10/channels/{AUTH_CHANNEL_ID}/messages?limit=100"
    headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            messages = response.json()
            keys = {}
            for msg in messages:
                content = msg.get("content", "")
                if "KEY:" in content:
                    # Parse: "KEY: Retri-XXXX | OP: Name"
                    try:
                        parts = content.split("|")
                        key_part = parts[0].replace("KEY:", "").strip()
                        op_part = parts[1].replace("OP:", "").strip() if len(parts) > 1 else "OPERATOR"
                        keys[key_part] = {"operator_id": op_part, "status": "active"}
                    except:
                        continue
            return keys
    except Exception as e:
        print(f"Auth Bridge Error: {e}")
    return {}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        key_input = query.get('pass', [None])[0]
        
        # 1. Check Admin Master Key
        if ADMIN_KEY and key_input == ADMIN_KEY:
            result = {
                "status": "success",
                "data": {"operator_id": ADMIN_OPERATOR, "status": "active", "role": "commander"}
            }
        # 2. Check Discord Vault Keys
        else:
            discord_keys = fetch_discord_keys()
            if key_input and key_input in discord_keys:
                result = {
                    "status": "success",
                    "data": discord_keys[key_input]
                }
            else:
                result = {
                    "status": "error",
                    "message": "INVALID_OR_EXPIRED_LICENSE"
                }
            
        self.wfile.write(json.dumps(result).encode())
