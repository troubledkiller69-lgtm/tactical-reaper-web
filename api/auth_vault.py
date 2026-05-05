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

# Emergency Fallback Key
LOCAL_KEYS = {
    "BIFROST-RECOVERY-2026": {"operator_id": "MASTER_ADMIN", "status": "active"}
}

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
        
        # Merge Discord keys with Local fallback
        discord_keys = fetch_discord_keys()
        all_keys = {**LOCAL_KEYS, **discord_keys}
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        if key_input and key_input in all_keys:
            result = {
                "status": "success",
                "data": all_keys[key_input]
            }
        else:
            result = {
                "status": "error",
                "message": "INVALID_OR_EXPIRED_LICENSE"
            }
            
        self.wfile.write(json.dumps(result).encode())
