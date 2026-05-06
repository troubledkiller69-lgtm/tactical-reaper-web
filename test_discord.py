import os
import sys
import json
import urllib.request
import urllib.error

# Load from .env file for local testing
try:
    with open(".env", "r") as f:
        for line in f:
            if line.startswith("DISCORD_TOKEN="):
                token = line.split("=")[1].strip()
            if line.startswith("AUTH_CHANNEL_ID="):
                channel = line.split("=")[1].strip()
except:
    print("Could not read .env")
    sys.exit(1)

print(f"Testing with Token: {token[:10]}...")
print(f"Testing with Channel: {channel}")

url = f"https://discord.com/api/v10/channels/{channel}/messages"
headers = {
    "Authorization": f"Bot {token}",
    "Content-Type": "application/json"
}
data = json.dumps({"content": "BIFROST_DIAGNOSTIC_PING"}).encode()

req = urllib.request.Request(url, data=data, headers=headers, method="POST")

try:
    res = urllib.request.urlopen(req)
    print("SUCCESS! Discord API returned HTTP", res.getcode())
except urllib.error.HTTPError as e:
    print(f"FAILED! Discord API returned HTTP {e.code}")
    print("Reason:", e.read().decode())
except Exception as e:
    print(f"CRASH: {e}")
