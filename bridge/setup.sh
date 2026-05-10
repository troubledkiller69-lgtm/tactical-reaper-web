#!/bin/bash
# ============================================================
# BIFROST ARTERY BRIDGE v2.0 — VPS Setup Script
# Debian 12 / Ubuntu 22.04
# ============================================================
set -e

echo "============================================"
echo "  BIFROST ARTERY BRIDGE — SETUP"
echo "============================================"

# --- System Update ---
apt update && apt upgrade -y

# --- Install Asterisk + Dependencies ---
apt install -y asterisk asterisk-core-sounds-en-wav \
    python3 python3-pip python3-venv \
    curl wget ffmpeg sox libsox-fmt-mp3 \
    ufw

# --- Create Bridge Directory ---
mkdir -p /opt/bifrost
mkdir -p /var/lib/asterisk/sounds/bifrost
mkdir -p /opt/bifrost/audio

# --- Copy Bridge Server ---
cp /root/bridge/server.py /opt/bifrost/server.py
cp /root/bridge/agi_capture.sh /opt/bifrost/agi_capture.sh
chmod +x /opt/bifrost/agi_capture.sh

# --- Python Virtual Env ---
python3 -m venv /opt/bifrost/venv
source /opt/bifrost/venv/bin/activate
pip install flask requests gunicorn

# --- Asterisk Config ---
# Backup originals
cp /etc/asterisk/pjsip.conf /etc/asterisk/pjsip.conf.bak 2>/dev/null || true
cp /etc/asterisk/extensions.conf /etc/asterisk/extensions.conf.bak 2>/dev/null || true

# Deploy our configs
cp /root/bridge/pjsip.conf /etc/asterisk/pjsip.conf
cp /root/bridge/extensions.conf /etc/asterisk/extensions.conf

# --- Firewall ---
ufw allow 22/tcp        # SSH
ufw allow 8080/tcp      # Bridge API
ufw allow 5060/udp      # SIP Signaling
ufw allow 5060/tcp      # SIP Signaling (TCP)
ufw allow 10000:20000/udp  # RTP Media
ufw --force enable

# --- Restart Asterisk ---
systemctl enable asterisk
systemctl restart asterisk

# --- Create Systemd Service for Bridge ---
cat > /etc/systemd/system/bifrost-bridge.service << 'UNIT'
[Unit]
Description=BIFROST Artery Bridge Server
After=network.target asterisk.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/bifrost
ExecStart=/opt/bifrost/venv/bin/gunicorn -w 2 -b 0.0.0.0:8080 server:app
Restart=always
RestartSec=5
Environment=ELEVENLABS_API_KEY=sk_b2667d56649a88a8f48844d86b0566fe15d3bffb1abb07db

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable bifrost-bridge
systemctl start bifrost-bridge

echo ""
echo "============================================"
echo "  BIFROST ARTERY BRIDGE — ONLINE"
echo "  Bridge API: http://$(hostname -I | awk '{print $1}'):8080"
echo "  Asterisk:   $(asterisk -rx 'core show version' 2>/dev/null || echo 'starting...')"
echo "============================================"
