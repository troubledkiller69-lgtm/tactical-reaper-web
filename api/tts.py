import os
import json
import requests
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
            action = data.get('action', '')
            
            if action == 'generate':
                self.handle_generate(data)
            elif action == 'voices':
                self.handle_voices()
            else:
                self._json(400, {"error": "Invalid action"})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def handle_voices(self):
        api_key = os.getenv('ELEVENLABS_API_KEY')
        if not api_key:
            # Fallback mock voices if no API key
            voices = [
                {"voice_id": "21m00Tcm4llvDq8ikWAM", "name": "Rachel (Bank Support)"},
                {"voice_id": "AZnzlk1Xhk9W707y5Urt", "name": "Nicole (Security Dept)"},
                {"voice_id": "VR6AewuayH9o6v13W091", "name": "Professional Male"}
            ]
            self._json(200, {"voices": voices})
            return

        try:
            url = "https://api.elevenlabs.io/v1/voices"
            headers = {"xi-api-key": api_key}
            response = requests.get(url, headers=headers)
            self._json(200, response.json())
        except Exception as e:
            self._json(500, {"error": str(e)})

    def handle_generate(self, data):
        text = data.get('text', '')
        voice_id = data.get('voice_id', '21m00Tcm4llvDq8ikWAM')
        api_key = os.getenv('ELEVENLABS_API_KEY')
        
        if not text:
            self._json(400, {"error": "Text is required"})
            return

        if not api_key:
            # Mock success for UI development
            self._json(200, {"status": "mock_success", "url": "https://example.com/mock_audio.mp3"})
            return

        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": api_key
            }
            payload = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            response = requests.post(url, json=payload, headers=headers)
            
            # In a real Vercel/Serverless setup, we might upload to S3/Supabase Storage
            # For now, we'll return a placeholder or base64 (not ideal for long audio)
            # This logic assumes the middleman proxy handles the actual storage/fetch
            self._json(200, {"status": "success", "note": "Audio generated and ready for signaling"})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
