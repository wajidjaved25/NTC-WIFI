#!/bin/bash
# Deploy Enhanced AFAQ SMS Logging

echo "=========================================="
echo "Deploying AFAQ SMS Enhanced Logging"
echo "=========================================="
echo ""

# Navigate to project
cd /opt/ntc-wifi || { echo "Error: /opt/ntc-wifi not found"; exit 1; }

# Pull latest code
echo "[1/3] Pulling latest code from Git..."
git pull origin main
if [ $? -ne 0 ]; then
    echo "Error: Git pull failed"
    exit 1
fi
echo "✓ Code updated"
echo ""

# Restart backend
echo "[2/3] Restarting backend service..."
systemctl restart ntc-wifi-backend
sleep 3
if ! systemctl is-active --quiet ntc-wifi-backend; then
    echo "Error: Backend failed to start"
    systemctl status ntc-wifi-backend
    exit 1
fi
echo "✓ Backend restarted"
echo ""

# Show log monitoring command
echo "[3/3] Setup complete!"
echo ""
echo "=========================================="
echo "✓ AFAQ Enhanced Logging Deployed"
echo "=========================================="
echo ""
echo "To monitor AFAQ SMS logs in real-time:"
echo "  journalctl -u ntc-wifi-backend -f | grep --color -A 50 'AFAQ'"
echo ""
echo "To test:"
echo "  1. Request OTP from portal"
echo "  2. Watch the detailed logs appear"
echo "  3. Share the full log output for diagnosis"
echo ""
echo "Quick test command:"
echo "  curl -X POST http://192.168.3.252/api/public/send-otp \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"mobile\":\"03001234567\",\"cnic\":\"1234567890123\"}'"
echo ""
