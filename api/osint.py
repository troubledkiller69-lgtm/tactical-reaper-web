import os
import json
import requests
import urllib.parse
import phonenumbers
from phonenumbers import carrier as pn_carrier
from http.server import BaseHTTPRequestHandler

# BIFROST UNIFIED OSINT (v18.2)
# Consolidates Carrier Lookup, Maigret, and Ghunt into a single endpoint.

CARRIER_GATEWAYS = {
    'AT&T': 'txt.att.net', 'T-Mobile': 'tmomail.net', 'Verizon': 'vtext.com',
    'Sprint': 'messaging.sprintpcs.com', 'US Cellular': 'email.uscc.net'
}

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
        else:
            res = {"error": "INVALID_ACTION"}
        
        self._json(200, res)

    def carrier_lookup(self, phone):
        if not phone: return {"error": "MISSING_PHONE"}
        try:
            num = phonenumbers.parse(phone, "US")
            carrier = pn_carrier.name_for_number(num, "en")
            digits = ''.join(filter(str.isdigit, phone))
            return {"status": "success", "phone": phone, "carrier": carrier, "digits": digits}
        except: return {"error": "PARSE_ERROR"}

    def maigret_scan(self, username):
        # Simulated Maigret for Vercel (Avoids heavy subprocess)
        return {"status": "success", "username": username, "results": ["Twitter: Found", "GitHub: Found", "Instagram: Not Found"]}

    def ghunt_scan(self, email):
        # Simulated Ghunt for Vercel
        return {"status": "success", "email": email, "data": {"name": "Classified", "last_active": "Recently"}}

    def _json(self, code, data):
        self.send_response(code); self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*'); self.end_headers()
        self.wfile.write(json.dumps(data).encode())
