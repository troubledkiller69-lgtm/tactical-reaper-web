import os
import json
import asyncio
import threading
import urllib.request
import phonenumbers
from phonenumbers import carrier as pn_carrier

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import discord
from discord.ext import commands
import uvicorn

app = FastAPI(title="BIFROST CORE")

# Enable CORS for Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration from Hugging Face Secrets
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
AUTH_CHANNEL_ID = os.getenv("AUTH_CHANNEL_ID", "1501042968776147051").strip()
ADMIN_KEY = os.getenv("ADMIN_KEY", "").strip()
ADMIN_OPERATOR = os.getenv("ADMIN_OPERATOR", "ADMIN")

# ---------------------------------------------------------
# DISCORD BOT LOGIC
# ---------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"BIFROST Commander Bot Online as {bot.user}")

@bot.command()
async def ping(ctx):
    await ctx.send("BIFROST Uplink Active.")

def run_bot():
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)

# ---------------------------------------------------------
# AUTHENTICATION API
# ---------------------------------------------------------
import requests
import asyncio
import urllib3

# Disable insecure request warnings for diagnostic mode
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def discord_request(url, method="GET", body=None):
    try:
        if not DISCORD_TOKEN: 
            return 500, "MISSING_DISCORD_TOKEN_SECRET"
        
        token = DISCORD_TOKEN.strip()
        headers = {
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json"
        }
        
        # Diagnostic: Disable verify=False to bypass potential proxy SSL drops
        if method.upper() == "POST":
            response = requests.post(url, json=body, headers=headers, timeout=20, verify=False)
        else:
            response = requests.get(url, headers=headers, timeout=20, verify=False)
            
        return response.status_code, response.text
    except requests.exceptions.SSLError as e:
        return 500, f"SSL_ERROR: {str(e)}. This usually means the Hugging Face firewall is blocking Discord."
    except requests.exceptions.Timeout:
        return 500, "REQUEST_TIMEOUT: Discord API is not responding. Possible network block."
    except requests.exceptions.RequestException as e:
        return 500, f"REQUEST_ERROR: {str(e)}"
    except Exception as e:
        return 500, f"UNKNOWN_EXCEPTION: {str(e)}"

import time

def fetch_keys():
    if not AUTH_CHANNEL_ID: return {}, []
    url = f"https://discord.com/api/v10/channels/{AUTH_CHANNEL_ID}/messages?limit=50"
    code, messages = discord_request(url)
    keys = {}
    raw = []
    now = time.time()
    if code == 200 and messages:
        for msg in messages:
            content = msg.get("content", "")
            raw.append({"content": content, "timestamp": msg.get("timestamp"), "id": msg.get("id")})
            if "KEY:" in content:
                try:
                    parts = content.split("|")
                    k = parts[0].replace("KEY:", "").strip()
                    op = parts[1].replace("OP:", "").strip() if len(parts) > 1 else "OPERATOR"
                    role = "operator"
                    expires = 0
                    for p in parts:
                        p = p.strip()
                        if p.startswith("ROLE:"):
                            role = p.replace("ROLE:", "").strip().lower()
                        if p.startswith("EXPIRES:"):
                            try: expires = int(p.replace("EXPIRES:", "").strip())
                            except: expires = 0
                    # Skip expired keys
                    if expires > 0 and expires < now:
                        continue
                    keys[k] = {"operator_id": op, "status": "active", "role": role, "expires": expires}
                except: continue
    return keys, raw

@app.get("/api/auth")
async def get_auth(request: Request):
    action = request.query_params.get('action', 'verify')
    pass_key = request.query_params.get('pass')
    
    if action == 'debug':
        return {
            "channel_id": AUTH_CHANNEL_ID,
            "token_prefix": DISCORD_TOKEN[:10] if DISCORD_TOKEN else "None"
        }
    
    if action == 'verify':
        if ADMIN_KEY and pass_key == ADMIN_KEY:
            return {"status": "success", "data": {"operator_id": ADMIN_OPERATOR, "role": "commander"}}
        else:
            keys, _ = fetch_keys()
            if pass_key in keys:
                return {"status": "success", "data": keys[pass_key]}
            else:
                return {"status": "error", "message": "INVALID_KEY"}

    elif action == 'list':
        auth_key = request.headers.get('X-Admin-Key')
        if auth_key == ADMIN_KEY:
            _, raw = fetch_keys()
            return {"keys": raw}
        else:
            raise HTTPException(status_code=401, detail="UNAUTHORIZED")

@app.post("/api/auth")
async def post_auth(request: Request):
    auth_key = request.headers.get('X-Admin-Key')
    if auth_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="UNAUTHORIZED")

    try:
        body = await request.json()
        new_key = body.get('key')
        op = body.get('operator', 'OPERATOR')
        role = body.get('role', 'operator')
        expires = body.get('expires', 0)
        if not new_key: raise HTTPException(status_code=400, detail="MISSING_KEY")

        msg_content = f"KEY: {new_key} | OP: {op} | ROLE: {role} | EXPIRES: {expires}"
        url = f"https://discord.com/api/v10/channels/{AUTH_CHANNEL_ID}/messages"
        code, err_msg = discord_request(url, "POST", {"content": msg_content})
        
        if code in [200, 201]:
            return {"status": "deployed"}
        else:
            return {"status": "failed", "discord_error_code": code, "error": str(err_msg)}
    except Exception as e:
        return {"status": "failed", "discord_error_code": 500, "error": f"POST_AUTH_CRASH: {str(e)}"}

# ---------------------------------------------------------
# DISRUPTION API
# ---------------------------------------------------------
@app.post("/api/disruption")
async def disruption_api(request: Request):
    body = await request.json()
    mode = body.get('mode', 'sms')
    target = body.get('target')
    if mode == 'email':
        return {"error": "BREVO_RELAY_SUSPENDED"}
    
    return {"status": "complete", "message": f"Simulated SMS flood on {target}"}

# ---------------------------------------------------------
# OSINT API
# ---------------------------------------------------------
@app.get("/api/osint")
async def osint_api(request: Request):
    action = request.query_params.get('action', 'carrier')
    target = request.query_params.get('target')

    if action == 'carrier':
        if not target: return {"error": "MISSING_PHONE"}
        try:
            num = phonenumbers.parse(target, "US")
            carrier = pn_carrier.name_for_number(num, "en")
            digits = ''.join(filter(str.isdigit, target))
            return {"status": "success", "phone": target, "carrier": carrier, "digits": digits}
        except: return {"error": "PARSE_ERROR"}
    
    return {"status": "success", "message": "Simulated scan"}

@app.on_event("startup")
async def startup_event():
    # Start discord bot in background thread
    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860)
