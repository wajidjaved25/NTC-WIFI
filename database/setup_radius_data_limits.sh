#!/bin/bash
# ============================================
# FreeRADIUS Data Limits Setup Script
# ============================================
# 
# Run this script on your Ubuntu RADIUS server to enable data usage limits
# Usage: sudo bash setup_radius_data_limits.sh

echo "======================================"
echo "FreeRADIUS Data Limits Configuration"
echo "======================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo)"
    exit 1
fi

# Backup existing sqlcounter config
if [ -f /etc/freeradius/3.0/mods-available/sqlcounter ]; then
    cp /etc/freeradius/3.0/mods-available/sqlcounter /etc/freeradius/3.0/mods-available/sqlcounter.backup
    echo "✓ Backed up existing sqlcounter config"
fi

# Create sqlcounter configuration
cat > /etc/freeradius/3.0/mods-available/sqlcounter << 'EOF'
# Daily data usage counter (in bytes)
sqlcounter daily_data_counter {
    sql_module_instance = sql
    dialect = postgresql
    
    counter_name = Daily-Data-Usage
    check_name = Max-Daily-Data
    reply_name = Daily-Data-Remaining
    
    key = User-Name
    reset = daily
    
    query = "\
        SELECT COALESCE(SUM(acctinputoctets + acctoutputoctets), 0) \
        FROM radacct \
        WHERE username = '%{${key}}' \
        AND acctstarttime >= date_trunc('day', CURRENT_TIMESTAMP)"
}

# Monthly data usage counter (in bytes)
sqlcounter monthly_data_counter {
    sql_module_instance = sql
    dialect = postgresql
    
    counter_name = Monthly-Data-Usage
    check_name = Max-Monthly-Data
    reply_name = Monthly-Data-Remaining
    
    key = User-Name
    reset = monthly
    
    query = "\
        SELECT COALESCE(SUM(acctinputoctets + acctoutputoctets), 0) \
        FROM radacct \
        WHERE username = '%{${key}}' \
        AND acctstarttime >= date_trunc('month', CURRENT_TIMESTAMP)"
}
EOF

echo "✓ Created sqlcounter configuration"

# Enable sqlcounter module
cd /etc/freeradius/3.0/mods-enabled
if [ ! -L sqlcounter ]; then
    ln -s ../mods-available/sqlcounter .
    echo "✓ Enabled sqlcounter module"
else
    echo "✓ sqlcounter module already enabled"
fi

# Update default site to include counters
SITE_FILE="/etc/freeradius/3.0/sites-available/default"

# Check if counters are already added
if ! grep -q "daily_data_counter" "$SITE_FILE"; then
    # Find the authorize section and add counters after sql
    # This uses sed to add the counters after the sql module call
    sed -i '/^[[:space:]]*sql$/a\
\
        # Data usage counters\
        daily_data_counter\
        monthly_data_counter' "$SITE_FILE"
    
    echo "✓ Added data counters to authorize section"
else
    echo "✓ Data counters already in authorize section"
fi

# Test FreeRADIUS configuration
echo ""
echo "Testing FreeRADIUS configuration..."
freeradius -XC

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Configuration test passed"
    
    # Restart FreeRADIUS
    echo ""
    echo "Restarting FreeRADIUS..."
    systemctl restart freeradius
    
    if [ $? -eq 0 ]; then
        echo "✓ FreeRADIUS restarted successfully"
        echo ""
        echo "======================================"
        echo "✓ Data limits are now active!"
        echo "======================================"
        echo ""
        echo "How it works:"
        echo "- Set Max-Daily-Data in radcheck (in bytes)"
        echo "- 100 MB = 104857600 bytes"
        echo "- 1 GB = 1073741824 bytes"
        echo ""
        echo "Test with: radtest testuser password localhost 0 testing123"
    else
        echo "✗ Failed to restart FreeRADIUS"
        echo "Check logs: journalctl -u freeradius -n 50"
    fi
else
    echo ""
    echo "✗ Configuration test failed"
    echo "Please check the configuration manually"
fi
