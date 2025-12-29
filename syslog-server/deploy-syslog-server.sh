#!/bin/bash
# SYSLOG SERVER DEPLOYMENT SCRIPT
# Run on syslog server

echo "🚀 NTC WiFi Syslog Server Deployment"
echo "======================================"

# 1. Install PostgreSQL
echo "1. Installing PostgreSQL 14..."
sudo apt-get update
sudo apt-get install -y postgresql-14 postgresql-contrib-14

# 2. Install TimescaleDB
echo "2. Installing TimescaleDB..."
sudo add-apt-repository -y ppa:timescale/timescaledb-ppa
sudo apt-get update
sudo apt-get install -y timescaledb-2-postgresql-14

# 3. Tune PostgreSQL for TimescaleDB
echo "3. Tuning PostgreSQL..."
sudo timescaledb-tune --quiet --yes

# 4. Restart PostgreSQL
echo "4. Restarting PostgreSQL..."
sudo systemctl restart postgresql
sudo systemctl enable postgresql

# 5. Create database and user
echo "5. Creating database..."
sudo -u postgres psql << 'EOSQL'
CREATE DATABASE ntc_wifi_logs;
CREATE USER syslog_user WITH PASSWORD 'SecureLogPassword123';
GRANT ALL PRIVILEGES ON DATABASE ntc_wifi_logs TO syslog_user;
\c ntc_wifi_logs
CREATE EXTENSION IF NOT EXISTS timescaledb;
GRANT ALL ON SCHEMA public TO syslog_user;
\q
EOSQL

# 6. Create firewall logs table
echo "6. Creating firewall logs table..."
sudo -u postgres psql ntc_wifi_logs < /opt/syslog-receiver/create_database.sql

# 7. Install Python dependencies
echo "7. Installing Python dependencies..."
sudo apt-get install -y python3 python3-pip python3-venv

# 8. Create application directory
echo "8. Setting up application..."
sudo mkdir -p /opt/syslog-receiver
cd /opt/syslog-receiver

# 9. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 10. Install Python packages
pip install --upgrade pip
pip install sqlalchemy psycopg2-binary python-dotenv

# 11. Create .env file from example
echo "9. Creating .env file..."
if [ ! -f /opt/syslog-receiver/.env ]; then
    cp /opt/syslog-receiver/.env.example /opt/syslog-receiver/.env
    echo "⚠️  IMPORTANT: Edit /opt/syslog-receiver/.env and update MAIN_SERVER_IP"
else
    echo "✅ .env file already exists"
fi

# 12. Create systemd service for syslog receiver
echo "10. Creating systemd services..."
cat > /tmp/syslog-receiver.service << 'EOF'
[Unit]
Description=NTC WiFi Syslog Receiver
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/syslog-receiver
Environment="PATH=/opt/syslog-receiver/venv/bin"
ExecStart=/opt/syslog-receiver/venv/bin/python3 /opt/syslog-receiver/syslog_receiver.py

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/syslog-receiver.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable syslog-receiver

# 13. Create systemd service for session correlator
cat > /tmp/session-correlator.service << 'EOF'
[Unit]
Description=NTC WiFi Session Correlator
After=network.target postgresql.service syslog-receiver.service
Requires=postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/syslog-receiver
Environment="PATH=/opt/syslog-receiver/venv/bin"
ExecStart=/opt/syslog-receiver/venv/bin/python3 /opt/syslog-receiver/session_correlator.py

Restart=always
RestartSec=60
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/session-correlator.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable session-correlator

echo ""
echo "✅ Syslog server setup complete!"
echo ""
echo "⚠️  IMPORTANT NEXT STEPS:"
echo "1. Edit /opt/syslog-receiver/.env and update MAIN_SERVER_IP"
echo "2. Verify all settings in .env file"
echo "3. Start services: sudo systemctl start syslog-receiver session-correlator"
echo "4. Configure FortiGate to send logs to this server"
echo "5. Check logs: sudo journalctl -u syslog-receiver -f"
echo ""
echo "📝 Configuration file: /opt/syslog-receiver/.env"
echo "📊 Database retention: 1 YEAR (365 days)"
