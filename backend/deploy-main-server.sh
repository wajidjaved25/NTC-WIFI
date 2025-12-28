#!/bin/bash
# MAIN SERVER DEPLOYMENT SCRIPT
# Run on server: bash deploy-main-server.sh

echo "🚀 NTC WiFi Main Server Deployment"
echo "==================================="

# 1. Stop backend
echo "1. Stopping backend..."
sudo systemctl stop ntc-wifi-backend

# 2. Backup database
echo "2. Backing up database..."
sudo mkdir -p /backup/postgresql
sudo -u postgres pg_dump ntc_wifi_admin > /backup/postgresql/backup_$(date +%Y%m%d_%H%M%S).sql

# 3. Update PostgreSQL config
echo "3. Updating PostgreSQL config..."
sudo cp /etc/postgresql/14/main/postgresql.conf /etc/postgresql/14/main/postgresql.conf.backup
sudo cp postgresql-production.conf /etc/postgresql/14/main/postgresql.conf
sudo systemctl restart postgresql

# 4. Create indices
echo "4. Creating database indices..."
sudo -u postgres psql ntc_wifi_admin < create-indices.sql

# 5. Install Redis
echo "5. Installing Redis..."
sudo apt-get update
sudo apt-get install -y redis-server

# 6. Configure Redis
echo "6. Configuring Redis..."
sudo sed -i 's/^bind 127.0.0.1/bind 0.0.0.0/' /etc/redis/redis.conf
echo "requirepass YOUR_REDIS_PASSWORD" | sudo tee -a /etc/redis/redis.conf
echo "maxmemory 8gb" | sudo tee -a /etc/redis/redis.conf
echo "maxmemory-policy allkeys-lru" | sudo tee -a /etc/redis/redis.conf
sudo systemctl restart redis-server

# 7. Install PgBouncer
echo "7. Installing PgBouncer..."
sudo apt-get install -y pgbouncer
sudo cp pgbouncer.ini /etc/pgbouncer/

# 8. Setup systemd service
echo "8. Setting up systemd service..."
sudo cp ntc-wifi-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ntc-wifi-backend

# 9. Update .env
echo "9. Please manually update /opt/ntc-wifi/backend/.env with production values"
echo "   Reference: .env.production"

# 10. Start backend
echo "10. Starting backend..."
sudo systemctl start ntc-wifi-backend

echo ""
echo "✅ Deployment complete!"
echo "Check status: sudo systemctl status ntc-wifi-backend"
echo "View logs: sudo journalctl -u ntc-wifi-backend -f"
