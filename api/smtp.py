import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from http.server import BaseHTTPRequestHandler
import concurrent.futures

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
            action = data.get('action', 'blast')
            
            if action == 'blast':
                relays = data.get('relays', []) # List of {host, port, user, pass}
                target = data.get('target', '')
                subject = data.get('subject', 'Security Alert')
                body = data.get('body', '')
                amount = int(data.get('amount', 1))
                
                results = self.run_blast(relays, target, subject, body, amount)
                self._json(200, {
                    "status": "success",
                    "sent": results['success'],
                    "failed": results['failed']
                })
            else:
                self._json(400, {"error": "Invalid action"})
        except Exception as e:
            self._json(400, {"error": str(e)})

    def send_email(self, relay, target, subject, body):
        try:
            msg = MIMEMultipart()
            msg['From'] = relay['user']
            msg['To'] = target
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(relay['host'], relay['port'], timeout=10)
            server.starttls()
            server.login(relay['user'], relay['pass'])
            server.sendmail(relay['user'], target, msg.as_string())
            server.quit()
            return True
        except:
            return False

    def run_blast(self, relays, target, subject, body, amount):
        success = 0
        failed = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            for i in range(amount):
                relay = relays[i % len(relays)]
                futures.append(executor.submit(self.send_email, relay, target, subject, body))
            
            for future in concurrent.futures.as_completed(futures):
                if future.result():
                    success += 1
                else:
                    failed += 1
                    
        return {"success": success, "failed": failed}

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
