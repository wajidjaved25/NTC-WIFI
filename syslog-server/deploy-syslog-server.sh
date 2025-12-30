#!/bin/bash
# SYSLOG SERVER DEPLOYMENT SCRIPT - FIXED FOR UBUNTU 24.04
# Run on syslog server

echo "🚀 NTC WiFi Syslog Server Deployment"
echo "======================================"
echo "Ubuntu 24.04 detected - using PostgreSQL 16"
echo ""

# 1. Install PostgreSQL 16 (default for Ubuntu 24.04)
echo "1. Installing PostgreSQL 16..."
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib

# 2. Install TimescaleDB for PostgreSQL 16
echo "2. Installing TimescaleDB..."
# Add TimescaleDB repository for PostgreSQL 16
echo "deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/timescaledb.list
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/timescaledb.gpg
sudo apt-get update
sudo apt-get install -y timescaledb-2-postgresql-16

# 3. Tune PostgreSQL for TimescaleDB
echo "3. Tuning PostgreSQL..."
sudo timescaledb-tune --quiet --yes

# 4. Restart PostgreSQL
echo "4. Restarting PostgreSQL..."
sudo systemctl restart postgresql
sudo systemctl enable postgresql

# Wait for PostgreSQL to be ready
sleep 5

# 5. Create database and user
echo "5. Creating database..."
sudo -u postgres psql << 'EOSQL'
CREATE DATABASE ntc_wifi_logs;
CREATE USER syslog_user WITH PASSWORD 'SecureLogPassword123';
GRANT ALL PRIVILEGES ON DATABASE ntc_wifi_logs TO syslog_user;
\c ntc_wifi_logs
CREATE EXTENSION IF NOT EXISTS timescaledb;
GRANT ALL ON SCHEMA public TO syslog_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO syslog_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO syslog_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO syslog_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO syslog_user;
\q
EOSQL

# 6. Create firewall logs table
echo "6. Creating firewall logs table..."
sudo -u postgres psql ntc_wifi_logs < /opt/syslog-receiver/create_database.sql

# 7. Install Python dependencies
echo "7. Installing Python dependencies..."
sudo apt-get install -y python3 python3-pip python3-venv

# 8. Create application directory and setup
echo "8. Setting up application..."
sudo mkdir -p /opt/syslog-receiver
cd /opt/syslog-receiver

# 9. Create virtual environment
echo "9. Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 10. Install Python packages
echo "10. Installing Python packages..."
pip install --upgrade pip
pip install sqlalchemy psycopg2-binary python-dotenv

# 11. Create .env file
echo "11. Creating .env file..."
cat > /opt/syslog-receiver/.env << 'EOF'
# Main Server Connection (WiFi Portal)
MAIN_SERVER_IP=10.2.49.27
MAIN_DB_PORT=5432
MAIN_DB_NAME=ntc_wifi_admin
MAIN_DB_USER=ntc_admin
MAIN_DB_PASSWORD=NTCWifi2024!

# Local Database (Firewall Logs)
LOGS_DB_HOST=localhost
LOGS_DB_PORT=5432
LOGS_DB_NAME=ntc_wifi_logs
LOGS_DB_USER=syslog_user
LOGS_DB_PASSWORD=SecureLogPassword123

# Correlation Settings
CORRELATION_INTERVAL=300
LOOKBACK_MINUTES=30

# Syslog Receiver Settings
SYSLOG_HOST=0.0.0.0
SYSLOG_PORT=514
QUEUE_SIZE=20000
BATCH_SIZE=2000
BATCH_TIMEOUT=0.5
NUM_WORKERS=4
EOF

echo "⚠️  Please edit /opt/syslog-receiver/.env and update MAIN_SERVER_IP with your actual IP"

# 12. Create systemd service for syslog receiver
echo "12. Creating systemd services..."
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
echo "   nano /opt/syslog-receiver/.env"
echo "2. Verify all settings in .env file"
echo "3. Start services:"
echo "   sudo systemctl start syslog-receiver"
echo "   sudo systemctl start session-correlator"
echo "4. Configure FortiGate to send logs to this server (port 514/UDP)"
echo "5. Check logs:"
echo "   sudo journalctl -u syslog-receiver -f"
echo "   sudo journalctl -u session-correlator -f"
echo ""
echo "📝 Configuration file: /opt/syslog-receiver/.env"
echo "📊 Database: ntc_wifi_logs (PostgreSQL 16 + TimescaleDB)"
echo "📊 Retention: 1 YEAR (365 days)"
echo ""
echo "🔍 Verify PostgreSQL:"
echo "   sudo systemctl status postgresql"
echo "   sudo -u postgres psql -c 'SELECT version();'"
