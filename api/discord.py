from http.server import BaseHTTPRequestHandler
import json
import os
import uuid
import urllib.request
import urllib.parse
from discord_interactions import verify_key

# Load environment variables
DISCORD_PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY", "5220a38079df1ca3d1815354a55633d6a0a6d4df9316dc213d9fd253333bb824")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://smxpzldbxewcgrakaqhn.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_QviDYLWIVjVJl4N01Bqaug_ZgkNHcde")

def supabase_insert(table, data):
    """Lightweight Supabase insert using raw HTTP instead of the heavy SDK."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    payload = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=payload, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('apikey', SUPABASE_KEY)
    req.add_header('Authorization', f'Bearer {SUPABASE_KEY}')
    req.add_header('Prefer', 'return=minimal')
    with urllib.request.urlopen(req, timeout=3) as resp:
        return resp.getcode()

def supabase_update(table, match_col, match_val, data):
    """Lightweight Supabase update using raw HTTP."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?{match_col}=eq.{urllib.parse.quote(match_val)}"
    payload = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=payload, method='PATCH')
    req.add_header('Content-Type', 'application/json')
    req.add_header('apikey', SUPABASE_KEY)
    req.add_header('Authorization', f'Bearer {SUPABASE_KEY}')
    req.add_header('Prefer', 'return=minimal')
    with urllib.request.urlopen(req, timeout=3) as resp:
        return resp.getcode()

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. Verify the Signature
        signature = self.headers.get("X-Signature-Ed25519")
        timestamp = self.headers.get("X-Signature-Timestamp")
        
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        if not DISCORD_PUBLIC_KEY:
            self.send_response(500)
            self.end_headers()
            return

        try:
            is_valid = verify_key(raw_body, signature, timestamp, DISCORD_PUBLIC_KEY)
            if not is_valid:
                self.send_response(401)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b"invalid request signature")
                return
        except Exception:
            self.send_response(401)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"invalid request signature")
            return

        # 2. Parse the body
        try:
            body = json.loads(raw_body.decode('utf-8'))
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return

        # 3. Handle Ping
        if body.get("type") == 1: # InteractionType.PING
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"type": 1}).encode('utf-8'))
            return

        # 4. Handle Application Command
        if body.get("type") == 2: # InteractionType.APPLICATION_COMMAND
            data = body.get("data", {})
            if data.get("name") == "genkey":
                options = data.get("options", [])
                operator_id = "UNKNOWN"
                hours = 24
                
                for opt in options:
                    if opt["name"] == "operator_id":
                        operator_id = opt["value"]
                    elif opt["name"] == "hours":
                        hours = int(opt["value"])

                # Generate the key
                new_key = f"Retri-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"
                db_data = {
                    "key": new_key,
                    "operator_id": operator_id,
                    "duration_hours": hours,
                    "status": "active"
                }
                
                try:
                    supabase_insert("keys", db_data)
                    reply = {
                        "type": 4, # InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE
                        "data": {
                            "content": f"**🚀 NEW CLOUD LICENSE GENERATED**\n\n**Operator:** `{operator_id}`\n**Key:** `{new_key}`\n**Duration:** `{hours} hours`\n\n*Use BOTH to initialize the Tactical Reaper matrix.*"
                        }
                    }
                except Exception as e:
                    reply = {
                        "type": 4,
                        "data": {
                            "content": f"❌ **Database Error:** {e}"
                        }
                    }

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(reply).encode('utf-8'))
                return

            if data.get("name") == "revoke":
                options = data.get("options", [])
                target_key = None
                
                for opt in options:
                    if opt["name"] == "key":
                        target_key = opt["value"]

                if target_key:
                    try:
                        # Revoke the key
                        supabase_update("keys", "key", target_key, {"status": "revoked"})
                        reply = {
                            "type": 4,
                            "data": {
                                "content": f"🛑 **LICENSE REVOKED**\n\nThe key `{target_key}` has been permanently revoked."
                            }
                        }
                    except Exception as e:
                        reply = {
                            "type": 4,
                            "data": {
                                "content": f"❌ **Database Error:** {e}"
                            }
                        }
                else:
                    reply = {
                        "type": 4,
                        "data": {
                            "content": f"❌ **Missing key.** You must provide the key to revoke."
                        }
                    }

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(reply).encode('utf-8'))
                return

        # Fallback
        self.send_response(400)
        self.end_headers()
