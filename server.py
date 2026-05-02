import http.server
import socketserver
import threading

class handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers['Content-Length'])
        data = self.rfile.read(length).decode('utf-8')
        with open('c:/Users/howar/.gemini/antigravity/scratch/EniReper/key.txt', 'w') as f:
            f.write(data)
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        print('KEY RECEIVED')
        
        # Shutdown server in a new thread
        def shutdown():
            self.server.shutdown()
        threading.Thread(target=shutdown).start()
        
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

socketserver.TCPServer.allow_reuse_address = True
httpd = socketserver.TCPServer(('', 1337), handler)
print('Listening on 1337')
httpd.serve_forever()
