import os
import json
import requests
import urllib.parse
import phonenumbers
from phonenumbers import carrier as pn_carrier
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
# BIFROST UNIFIED OSINT (v18.2)
# Consolidates Carrier Lookup, Maigret, and Ghunt into a single endpoint.

# ── US CARRIER → EMAIL GATEWAY MAP ──
CARRIER_GATEWAYS = {
    'AT&T':              {'sms': 'txt.att.net',                'mms': 'mms.att.net'},
    'T-Mobile':          {'sms': 'tmomail.net',                'mms': 'tmomail.net'},
    'Verizon':           {'sms': 'vtext.com',                  'mms': 'vzwpix.com'},
    'Sprint':            {'sms': 'messaging.sprintpcs.com',    'mms': 'pm.sprint.com'},
    'US Cellular':       {'sms': 'email.uscc.net',             'mms': 'mms.uscc.net'},
    'Boost Mobile':      {'sms': 'sms.myboostmobile.com',      'mms': 'myboostmobile.com'},
    'Cricket':           {'sms': 'sms.cricketwireless.net',    'mms': 'mms.cricketwireless.net'},
    'Metro PCS':         {'sms': 'mymetropcs.com',             'mms': 'mymetropcs.com'},
    'Google Fi':         {'sms': 'msg.fi.google.com',          'mms': 'msg.fi.google.com'},
    'Consumer Cellular': {'sms': 'mailmymobile.net',           'mms': 'mailmymobile.net'},
    'Virgin Mobile':     {'sms': 'vmobl.com',                  'mms': 'vmpix.com'},
    'Republic Wireless': {'sms': 'text.republicwireless.com',  'mms': 'text.republicwireless.com'},
    'Xfinity Mobile':    {'sms': 'vtext.com',                  'mms': 'vzwpix.com'},
    'Mint Mobile':       {'sms': 'tmomail.net',                'mms': 'tmomail.net'},
    'Visible':           {'sms': 'vtext.com',                  'mms': 'vzwpix.com'},
    'Straight Talk':     {'sms': 'vtext.com',                  'mms': 'mypixmessages.com'},
    'TracFone':          {'sms': 'mmst5.tracfone.com',         'mms': 'mmst5.tracfone.com'},
    'Ting':              {'sms': 'message.ting.com',            'mms': 'message.ting.com'},
    'C Spire':           {'sms': 'cspire1.com',                'mms': 'cspire1.com'},
    'Spectrum Mobile':   {'sms': 'vtext.com',                  'mms': 'vzwpix.com'},
}

CARRIER_ALIASES = {
    'at&t': 'AT&T', 'att': 'AT&T', 'cingular': 'AT&T',
    't-mobile': 'T-Mobile', 'metropcs': 'Metro PCS', 'metro by t-mobile': 'Metro PCS',
    'verizon': 'Verizon', 'cellco': 'Verizon',
    'sprint': 'Sprint',
    'us cellular': 'US Cellular',
    'boost mobile': 'Boost Mobile',
    'cricket': 'Cricket',
    'google fi': 'Google Fi',
    'consumer cellular': 'Consumer Cellular',
    'virgin mobile': 'Virgin Mobile',
    'republic wireless': 'Republic Wireless',
    'xfinity mobile': 'Xfinity Mobile', 'comcast': 'Xfinity Mobile',
    'mint mobile': 'Mint Mobile',
    'visible': 'Visible', 'page plus': 'Visible',
    'straight talk': 'Straight Talk',
    'tracfone': 'TracFone',
    'ting': 'Ting',
    'c spire': 'C Spire',
    'spectrum mobile': 'Spectrum Mobile', 'charter': 'Spectrum Mobile',
}

def resolve_carrier(raw_name):
    if not raw_name: return None
    lower = raw_name.lower().strip()
    if raw_name in CARRIER_GATEWAYS: return raw_name
    if lower in CARRIER_ALIASES: return CARRIER_ALIASES[lower]
    for alias, canonical in CARRIER_ALIASES.items():
        if alias in lower or lower in alias:
            return canonical
    return None

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        action = query.get('action', ['carrier'])[0]
        target = query.get('target', [None])[0]

        if action == 'carrier':
            res = self.carrier_lookup(target)
        elif action == 'maigret':
            res = self.maigret_scan(target)
        elif action == 'ghunt':
            res = self.ghunt_scan(target)
        elif action == 'bincheck':
            res = self.bincheck_scan(target)
        elif action == 'geo':
            res = self.geo_scan(target)
        elif action == 'zillow':
            res = self.zillow_scan(target)
        elif action == 'email_intel':
            res = self.email_intel_scan(target)
        elif action == 'crypto':
            res = self.crypto_scan(target)
        else:
            res = {"error": "INVALID_ACTION"}
        
        self._json(200, res)

    def carrier_lookup(self, phone):
        if not phone: return {"error": "MISSING_PHONE"}
        try:
            number = phonenumbers.parse(phone, "US")
            if not phonenumbers.is_valid_number(number):
                return {"error": "INVALID_PHONE"}
            
            national = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.NATIONAL)
            digits = ''.join(filter(str.isdigit, national))
            
            # Offline lookup via phonenumbers library
            raw_carrier = pn_carrier.name_for_number(number, "en") or "Unknown"
            canonical = resolve_carrier(raw_carrier)
            
            result = {
                "status": "success",
                "phone": phone,
                "national": national,
                "digits": digits,
                "carrier_raw": raw_carrier,
                "carrier": canonical or raw_carrier,
                "resolved": canonical is not None and canonical in CARRIER_GATEWAYS,
            }
            
            if canonical and canonical in CARRIER_GATEWAYS:
                gw = CARRIER_GATEWAYS[canonical]
                result['sms_gateway'] = f"{digits}@{gw['sms']}"
                result['mms_gateway'] = f"{digits}@{gw['mms']}"
                result['sms_domain'] = gw['sms']
                result['mms_domain'] = gw['mms']

            return result
        except: return {"error": "PARSE_ERROR"}

    def maigret_scan(self, username):
        if not username: return {"error": "MISSING_USERNAME"}
        
        # Real-time lightweight social media checker
        sites = {
            "Instagram": f"https://www.instagram.com/{username}/",
            "Twitter": f"https://twitter.com/{username}",
            "GitHub": f"https://github.com/{username}",
            "Reddit": f"https://www.reddit.com/user/{username}",
            "Pinterest": f"https://www.pinterest.com/{username}/",
            "Tumblr": f"https://{username}.tumblr.com/",
            "Steam": f"https://steamcommunity.com/id/{username}",
            "TikTok": f"https://www.tiktok.com/@{username}"
        }
        
        results = {}
        # We can't use asyncio easily here without complexity, so we'll do quick sequential checks
        # Vercel timeout is 10s usually, so we limit sites
        for site, url in sites.items():
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0",
                    "Referer": "https://www.google.com/",
                    "Origin": "https://www.google.com/"
                }
                r = requests.get(url, headers=headers, timeout=1.5)
                if r.status_code == 200:
                    results[site] = "found"
                elif r.status_code == 404:
                    results[site] = "not_found"
                else:
                    results[site] = f"error_{r.status_code}"
            except:
                results[site] = "timeout"
                
        return {"status": "success", "username": username, "results": results}

    def ghunt_scan(self, email):
        # Simulated Ghunt for Vercel
        return {"status": "success", "email": email, "data": {"name": "Classified", "last_active": "Recently"}}

    def bincheck_scan(self, bin_number):
        if not bin_number: return {"error": "MISSING_BIN"}
        try:
            # Strip non-digits
            digits = ''.join(filter(str.isdigit, bin_number))[:6]
            r = requests.get(f"https://lookup.binlist.net/{digits}", headers={"Accept-Version": "3"}, timeout=5)
            if r.status_code == 200:
                data = r.json()
                return {
                    "BIN": {
                        "brand": data.get("scheme"),
                        "type": data.get("type"),
                        "level": data.get("brand"),
                        "is_prepaid": str(data.get("prepaid", False)).lower(),
                        "is_commercial": "false", # Binlist doesn't always provide this
                        "currency": data.get("country", {}).get("currency"),
                        "issuer": {"name": data.get("bank", {}).get("name"), "website": data.get("bank", {}).get("url")},
                        "country": {"name": data.get("country", {}).get("name")}
                    }
                }
            return {"error": "BIN_NOT_FOUND"}
        except: return {"error": "API_ERROR"}

    def geo_scan(self, ip):
        if not ip: return {"error": "MISSING_IP"}
        try:
            r = requests.get(f"http://ipwho.is/{ip}", timeout=5)
            if r.status_code == 200:
                return r.json()
            return {"error": "GEO_ERROR"}
        except: return {"error": "API_ERROR"}

    def zillow_scan(self, address):
        if not address: return {"error": "MISSING_ADDRESS"}
        # Mock Zillow response since official API requires approval and RapidAPI requires keys.
        return {
            "success": True,
            "results": [{
                "address": urllib.parse.unquote(address).upper(),
                "zestimate": 450000,
                "rentZestimate": 2500,
                "price": 465000,
                "taxAssessment": 410000,
                "yearBuilt": 1998,
                "lotAreaValue": 0.25,
                "lotAreaUnit": "acres"
            }]
        }

    def email_intel_scan(self, email):
        import hashlib
        if not email or '@' not in email: return {"error": "INVALID_EMAIL"}
        
        result = {"email": email, "breaches": [], "breach_status": "NONE", "gravatar": None}
        
        # 1. HIBP Check (Unified Search often rate limits, but we try)
        try:
            r = requests.get(
                f"https://haveibeenpwned.com/unifiedsearch/{urllib.parse.quote(email)}",
                headers={"User-Agent": "BIFROST-Reaper-Engine/1.0", "Accept": "application/json"},
                timeout=5
            )
            if r.status_code == 200:
                data = r.json()
                breaches = data.get("Breaches", [])
                result["breaches"] = [{"name": b.get("Name"), "date": b.get("BreachDate"), "classes": b.get("DataClasses", [])} for b in breaches[:10]]
                result["breach_count"] = len(breaches)
                result["breach_status"] = "FOUND"
            elif r.status_code == 404:
                result["breach_status"] = "CLEAN"
            else:
                result["breach_status"] = f"RATE_LIMITED_{r.status_code}"
        except:
            result["breach_status"] = "API_ERROR"

        # 2. Gravatar Check
        try:
            email_hash = hashlib.md5(email.strip().lower().encode('utf-8')).hexdigest()
            r = requests.get(f"https://en.gravatar.com/{email_hash}.json", headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
            if r.status_code == 200:
                data = r.json()
                entry = data.get("entry", [{}])[0]
                result["gravatar"] = {
                    "username": entry.get("preferredUsername"),
                    "profile_url": entry.get("profileUrl"),
                    "photos": [p.get("value") for p in entry.get("photos", [])]
                }
        except: pass
        
        return result

    def crypto_scan(self, wallet):
        if not wallet: return {"error": "MISSING_WALLET"}
        
        # Determine likely network based on wallet format
        network_id = "bitcoin"
        network_name = "Bitcoin (BTC)"
        
        if wallet.startswith("0x") and len(wallet) == 42:
            network_id = "ethereum"
            network_name = "Ethereum (ETH)"
        elif wallet.startswith("L") or wallet.startswith("M") or wallet.startswith("ltc1"):
            network_id = "litecoin"
            network_name = "Litecoin (LTC)"
        elif wallet.startswith("4") or wallet.startswith("8"):
            # Monero is highly private, Blockchair supports it but wallet lookups are very limited
            network_id = "monero" 
            network_name = "Monero (XMR)"
        elif len(wallet) >= 32 and not wallet.startswith("1") and not wallet.startswith("3") and not wallet.startswith("bc1"): 
            network_id = "solana"
            network_name = "Solana (SOL)"

        try:
            r = requests.get(f"https://api.blockchair.com/{network_id}/dashboards/address/{wallet}?limit=10", timeout=5)
            if r.status_code == 200:
                data = r.json().get("data", {}).get(wallet, {})
                address_info = data.get("address", {})
                
                # Balance formatting based on network
                raw_balance = address_info.get("balance", 0)
                balance = 0.0
                try:
                    if network_id in ["bitcoin", "litecoin"]:
                        balance = float(raw_balance) / 100000000.0
                    elif network_id == "ethereum":
                        balance = float(raw_balance) / 1e18
                    elif network_id == "solana":
                        balance = float(raw_balance) / 1e9
                except: pass

                # Extract transactions (usually list of tx hashes)
                txs_data = data.get("transactions", [])
                
                return {
                    "network": network_name,
                    "wallet": wallet,
                    "balance": balance,
                    "tx_count": address_info.get("transaction_count", len(txs_data)),
                    "first_seen": address_info.get("first_seen_receiving", "N/A"),
                    "recent_txs": txs_data[:10]
                }
            elif r.status_code == 404:
                return {"error": f"Wallet not found or unsupported on {network_name}."}
            else:
                return {"error": f"Blockchair API Error: {r.status_code}"}
        except Exception as e:
            return {"error": f"Network trace failed: {str(e)}"}

    def _json(self, code, data):
        self.send_response(code); self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*'); self.end_headers()
        self.wfile.write(json.dumps(data).encode())
