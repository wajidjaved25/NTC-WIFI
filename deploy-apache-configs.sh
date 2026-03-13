#!/bin/bash
# Deploy Fixed Apache Configs for NTC WiFi
# Fixes iPhone captive portal caching issue

echo "==================================="
echo "NTC WiFi - Apache Config Deployment"
echo "==================================="
echo ""

# Backup existing configs
echo "[1/5] Backing up existing configs..."
cp /etc/apache2/sites-available/ntc-wifi.conf /etc/apache2/sites-available/ntc-wifi.conf.backup-$(date +%Y%m%d-%H%M%S)
cp /etc/apache2/sites-available/ntc-wifi-ssl.conf /etc/apache2/sites-available/ntc-wifi-ssl.conf.backup-$(date +%Y%m%d-%H%M%S)
echo "✓ Backups created"
echo ""

# Deploy HTTP config
echo "[2/5] Deploying HTTP config (ntc-wifi.conf)..."
cat > /etc/apache2/sites-available/ntc-wifi.conf << 'HTTPEOF'
# NTC WiFi HTTP Configuration

<VirtualHost *:80>
    ServerName 192.168.3.252
    
    # CAPTIVE PORTAL DETECTION - iOS
    Redirect 302 /hotspot-detect.html http://192.168.3.252/portal/index.html?v=3
    Redirect 302 /library/test/success.html http://192.168.3.252/portal/index.html?v=3
    Redirect 302 /success.txt http://192.168.3.252/portal/index.html?v=3
    
    # CAPTIVE PORTAL DETECTION - Android
    Redirect 302 /generate_204 http://192.168.3.252/portal/index.html?v=3
    Redirect 302 /gen_204 http://192.168.3.252/portal/index.html?v=3
    
    # CAPTIVE PORTAL DETECTION - Windows
    Redirect 302 /ncsi.txt http://192.168.3.252/portal/index.html?v=3
    Redirect 302 /connecttest.txt http://192.168.3.252/portal/index.html?v=3
    
    # PUBLIC WIFI PORTAL
    Alias /portal /opt/ntc-wifi/public-portal/dist
    <Directory /opt/ntc-wifi/public-portal/dist>
        Require all granted
        DirectoryIndex index.html
        
        # PREVENT CACHING FOR CAPTIVE PORTAL
        Header set Cache-Control "no-cache, no-store, must-revalidate"
        Header set Pragma "no-cache"
        Header set Expires "0"

        AddType text/css .css
        AddType application/javascript .js
        AddType application/json .json
        AddType image/svg+xml .svg

        RewriteEngine On
        RewriteBase /portal/
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule . /portal/index.html [L]
    </Directory>

    # BACKEND API PROXY
    ProxyPreserveHost On
    ProxyTimeout 300
    
    <Location /api/>
        Header always set Access-Control-Allow-Origin "*"
        Header always set Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS"
        Header always set Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With"
        
        ProxyPass http://127.0.0.1:8000/api/
        ProxyPassReverse http://127.0.0.1:8000/api/
    </Location>

    ErrorLog ${APACHE_LOG_DIR}/ntc-wifi-error.log
    CustomLog ${APACHE_LOG_DIR}/ntc-wifi-access.log combined
</VirtualHost>

# APPLE CAPTIVE PORTAL DETECTION DOMAINS
<VirtualHost *:80>
    ServerName captive.apple.com
    ServerAlias www.apple.com
    
    RedirectMatch 302 ^/.*$ http://192.168.3.252/portal/index.html?v=3
    
    ErrorLog ${APACHE_LOG_DIR}/ntc-wifi-error.log
    CustomLog ${APACHE_LOG_DIR}/ntc-wifi-access.log combined
</VirtualHost>

# ANDROID CAPTIVE PORTAL DETECTION DOMAINS
<VirtualHost *:80>
    ServerName connectivitycheck.gstatic.com
    ServerAlias clients3.google.com
    ServerAlias www.google.com
    
    RedirectMatch 302 ^/.*$ http://192.168.3.252/portal/index.html?v=3
    
    ErrorLog ${APACHE_LOG_DIR}/ntc-wifi-error.log
    CustomLog ${APACHE_LOG_DIR}/ntc-wifi-access.log combined
</VirtualHost>
HTTPEOF
echo "✓ HTTP config deployed"
echo ""

# Deploy HTTPS config
echo "[3/5] Deploying HTTPS config (ntc-wifi-ssl.conf)..."
cat > /etc/apache2/sites-available/ntc-wifi-ssl.conf << 'HTTPSEOF'
# NTC WiFi HTTPS Configuration - ADMIN PANEL ONLY
# NOTE: Captive portal MUST use HTTP (port 80)

<VirtualHost *:443>
    ServerName pmfreewifi.ntc.org.pk
    ServerAlias admin.ntc.org.pk
    ServerAlias *.ntc.org.pk

    SSLEngine on
    SSLCertificateFile /etc/ssl/ntc/fullchain.pem
    SSLCertificateKeyFile /etc/ssl/ntc/ntc_org_pk.key
    SSLProtocol all -SSLv3 -TLSv1 -TLSv1.1
    SSLCipherSuite HIGH:!aNULL:!MD5
    SSLHonorCipherOrder on

    Header always set Strict-Transport-Security "max-age=31536000"
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-XSS-Protection "1; mode=block"

    <Location />
        Require ip 192.168.0.0/22
        Require ip 127.0.0.1
        Require ip ::1
    </Location>

    Timeout 300
    ErrorLog ${APACHE_LOG_DIR}/ntc-wifi-ssl-error.log
    CustomLog ${APACHE_LOG_DIR}/ntc-wifi-ssl-access.log combined

    # ADMIN PORTAL
    DocumentRoot /opt/ntc-wifi/frontend/dist
    <Directory /opt/ntc-wifi/frontend/dist>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require ip 192.168.0.0/22
        DirectoryIndex index.html

        RewriteEngine On
        RewriteBase /
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteCond %{REQUEST_URI} !^/api
        RewriteCond %{REQUEST_URI} !^/media
        RewriteCond %{REQUEST_URI} !^/static
        RewriteRule . /index.html [L]

        <FilesMatch "\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf)$">
            Header set Cache-Control "public, max-age=604800, immutable"
        </FilesMatch>
    </Directory>

    # BACKEND API
    ProxyPreserveHost On
    ProxyTimeout 300

    <Location /api/>
        Require ip 192.168.0.0/22
        Header always set Access-Control-Allow-Origin "*"
        Header always set Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS"
        Header always set Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With"
        Header always set Access-Control-Allow-Credentials "true"
        Header always set Access-Control-Max-Age "3600"

        ProxyPass http://127.0.0.1:8000/api/
        ProxyPassReverse http://127.0.0.1:8000/api/

        RequestHeader set X-Forwarded-Proto "https"
        RequestHeader set X-Forwarded-For "%{REMOTE_ADDR}s"
        RequestHeader set X-Real-IP "%{REMOTE_ADDR}s"
    </Location>

    <LocationMatch "^/api/">
        <Limit OPTIONS>
            Require ip 192.168.0.0/22
        </Limit>
    </LocationMatch>

    <Location /health>
        ProxyPass http://127.0.0.1:8000/api/health
        ProxyPassReverse http://127.0.0.1:8000/api/health
        Require ip 192.168.0.0/22
    </Location>

    # MEDIA & STATIC FILES
    Alias /media /opt/ntc-wifi/media
    <Directory /opt/ntc-wifi/media>
        Options -Indexes +FollowSymLinks
        AllowOverride None
        Require ip 192.168.0.0/22

        <FilesMatch "\.(png|jpg|jpeg|gif|ico|svg|mp4|webm|pdf)$">
            Header set Cache-Control "public, max-age=604800"
        </FilesMatch>
    </Directory>

    Alias /static /opt/ntc-wifi/backend/static
    <Directory /opt/ntc-wifi/backend/static>
        Options -Indexes +FollowSymLinks
        AllowOverride None
        Require ip 192.168.0.0/22

        <FilesMatch "\.(css|js|png|jpg|jpeg|gif|ico|svg)$">
            Header set Cache-Control "public, max-age=604800"
        </FilesMatch>
    </Directory>

</VirtualHost>
HTTPSEOF
echo "✓ HTTPS config deployed"
echo ""

# Test config
echo "[4/5] Testing Apache configuration..."
apache2ctl configtest
if [ $? -ne 0 ]; then
    echo "✗ Apache config test FAILED!"
    echo "  Restoring backups..."
    mv /etc/apache2/sites-available/ntc-wifi.conf.backup-* /etc/apache2/sites-available/ntc-wifi.conf 2>/dev/null
    mv /etc/apache2/sites-available/ntc-wifi-ssl.conf.backup-* /etc/apache2/sites-available/ntc-wifi-ssl.conf 2>/dev/null
    exit 1
fi
echo "✓ Config test passed"
echo ""

# Restart Apache
echo "[5/5] Restarting Apache..."
systemctl restart apache2
if [ $? -ne 0 ]; then
    echo "✗ Apache restart FAILED!"
    systemctl status apache2
    exit 1
fi
echo "✓ Apache restarted successfully"
echo ""

echo "==================================="
echo "✓ Deployment Complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. On iPhone: Settings → General → Transfer or Reset → Reset Network Settings"
echo "2. Reconnect to WiFi"
echo "3. Portal should now show correctly with ?v=3 cache buster"
echo ""
echo "Monitor logs: tail -f /var/log/apache2/ntc-wifi-access.log | grep -i 'apple\\|hotspot'"
echo ""
