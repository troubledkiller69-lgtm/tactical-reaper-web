#!/bin/bash
# ============================================================
# BIFROST ARTERY BRIDGE — One-Click Deploy
# Run this on the VPS as root
# Usage: bash deploy.sh
# ============================================================
set -e

echo ""
echo "=========================================="
echo "  BIFROST ARTERY BRIDGE — DEPLOYING"
echo "=========================================="

# Create directories
mkdir -p /opt/bifrost
mkdir -p /root/bridge
mkdir -p /var/lib/asterisk/sounds/bifrost

# --- System Update ---
echo "[1/6] Updating system..."
apt update -qq && apt upgrade -y -qq

# --- Install Packages ---
echo "[2/6] Installing Asterisk + dependencies..."
DEBIAN_FRONTEND=noninteractive apt install -y -qq \
    asterisk \
    python3 python3-pip python3-venv \
    curl wget ffmpeg sox libsox-fmt-mp3 \
    ufw espeak > /dev/null 2>&1

# --- Python Environment ---
echo "[3/6] Setting up Python environment..."
python3 -m venv /opt/bifrost/venv
/opt/bifrost/venv/bin/pip install flask requests gunicorn -q

# --- Copy Files ---
echo "[4/6] Deploying bridge files..."
cp /root/bridge/server.py /opt/bifrost/server.py
cp /root/bridge/agi_capture.sh /opt/bifrost/agi_capture.sh
chmod +x /opt/bifrost/agi_capture.sh

# --- Asterisk Config ---
echo "[5/6] Configuring Asterisk..."
cp /etc/asterisk/pjsip.conf /etc/asterisk/pjsip.conf.bak 2>/dev/null || true
cp /etc/asterisk/extensions.conf /etc/asterisk/extensions.conf.bak 2>/dev/null || true
cp /root/bridge/pjsip.conf /etc/asterisk/pjsip.conf
cp /root/bridge/extensions.conf /etc/asterisk/extensions.conf

# Restart Asterisk
systemctl enable asterisk
systemctl restart asterisk

# --- Bridge Service ---
echo "[6/6] Starting bridge service..."
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

# --- Firewall ---
ufw allow 22/tcp
ufw allow 8080/tcp
ufw allow 5060/udp
ufw allow 5060/tcp
ufw allow 10000:20000/udp
ufw --force enable

# --- Status Check ---
echo ""
echo "=========================================="
echo "  BIFROST ARTERY BRIDGE — DEPLOYED"
echo "=========================================="
echo "  Bridge:   http://$(hostname -I | awk '{print $1}'):8080/health"
echo "  Asterisk: $(asterisk -rx 'pjsip show registrations' 2>/dev/null | head -5 || echo 'starting...')"
echo ""
echo "  Test: curl http://localhost:8080/health"
echo "=========================================="
