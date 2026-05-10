#!/bin/bash
# ============================================================
# BIFROST AGI Capture Script
# Called by Asterisk when DTMF digits are captured
# Sends OTP to the bridge server via HTTP
# ============================================================

CALL_ID="$1"
DIGITS="$2"
BRIDGE_URL="http://127.0.0.1:8080"

# Read AGI environment (required by AGI protocol)
while read line; do
    [ "$line" = "" ] && break
done

# Send captured digits to bridge
curl -s -X POST "${BRIDGE_URL}/captured?call_id=${CALL_ID}&digits=${DIGITS}" > /dev/null 2>&1

# AGI response
echo "SET VARIABLE CAPTURE_STATUS success"
echo ""
