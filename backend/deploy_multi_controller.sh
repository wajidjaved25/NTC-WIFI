#!/bin/bash

# Multi-Controller Migration & Deployment Script
# This script will migrate the database and restart services

echo "=========================================="
echo "Multi-Controller Migration & Deployment"
echo "=========================================="
echo ""

# Navigate to backend directory
cd /opt/ntc-wifi/backend

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "[0/4] Activating virtual environment..."
    source venv/bin/activate
    echo "  ✓ Virtual environment activated"
else
    echo "⚠ Warning: No virtual environment found at /opt/ntc-wifi/backend/venv"
    echo "  Attempting to run without venv..."
fi

echo ""

# Run migration
echo "[1/4] Running database migration..."
python3 migrate_multi_controller.py

if [ $? -ne 0 ]; then
    echo "✗ Migration failed! Please check the error above."
    exit 1
fi

echo ""
echo "[2/4] Restarting backend service..."
systemctl restart ntc-wifi-backend

echo ""
echo "[3/4] Rebuilding frontend..."
cd /opt/ntc-wifi/frontend
npm run build

echo ""
echo "[4/4] Restarting Apache..."
systemctl restart apache2

echo ""
echo "=========================================="
echo "✓✓✓ DEPLOYMENT COMPLETE ✓✓✓"
echo "=========================================="
echo ""
echo "Your system now supports multiple controllers with automatic failover!"
echo "Access the admin panel to:"
echo "  1. View your existing controller (now set as Primary)"
echo "  2. Add backup controllers"
echo "  3. Monitor health status"
echo ""
echo "Visit: https://your-server/admin"
echo ""
