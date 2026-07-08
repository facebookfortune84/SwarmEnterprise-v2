#!/bin/bash
# Production Deployment Configuration Guide
# SwarmOS Backend - API & Monitoring Stack

# ===================================================================
# 1. DNS CONFIGURATION (Configure at your registrar)
# ===================================================================
# For example, with Cloudflare, IONOS, GoDaddy, etc.

# Primary API domain
# Type: A Record
# Name: api.realms2riches.com
# Value: YOUR_SERVER_IP
# TTL: 300 (5 minutes)

# Monitoring subdomains
# Type: A Record
# Name: monitoring.realms2riches.com
# Value: YOUR_SERVER_IP
# TTL: 300

# Web dashboard
# Type: A Record
# Name: realms2riches.com
# Value: YOUR_SERVER_IP
# TTL: 300

echo "📍 DNS Configuration:"
echo "  1. Point api.realms2riches.com to your server IP"
echo "  2. Point monitoring.realms2riches.com to your server IP"
echo "  3. Point realms2riches.com to your server IP"
echo "  4. Wait 5-15 minutes for DNS propagation"

# ===================================================================
# 2. SSL/TLS CERTIFICATES (Let's Encrypt with Certbot)
# ===================================================================

# Install certbot
# sudo apt-get install certbot python3-certbot-nginx

# Generate certificates
# sudo certbot certonly --standalone \
#   -d api.realms2riches.com \
#   -d monitoring.realms2riches.com \
#   -d realms2riches.com \
#   --email ops@realms2riches.com \
#   --agree-tos \
#   --non-interactive

# Auto-renewal (runs twice daily)
# sudo systemctl enable certbot.timer

# Certificates location:
# /etc/letsencrypt/live/api.realms2riches.com/fullchain.pem
# /etc/letsencrypt/live/api.realms2riches.com/privkey.pem

echo "🔒 SSL Configuration:"
echo "  Certificates: /etc/letsencrypt/live/api.realms2riches.com/"
echo "  Auto-renewal: sudo systemctl status certbot.timer"

# ===================================================================
# 3. NGINX REVERSE PROXY WITH SSL
# ===================================================================

# Create SSL-enabled nginx config at /etc/nginx/sites-available/swarmos-ssl

cat > /tmp/swarmos-ssl.conf << 'NGINX_CONFIG'
# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name api.realms2riches.com monitoring.realms2riches.com realms2riches.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS API Gateway
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.realms2riches.com;

    ssl_certificate /etc/letsencrypt/live/api.realms2riches.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.realms2riches.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    client_max_body_size 100M;

    # Backend proxy
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_redirect off;

        # Timeouts for long-running requests
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Rate limiting (adjust as needed)
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=20 nodelay;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
}

# HTTPS Monitoring (Prometheus + Grafana)
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name monitoring.realms2riches.com;

    ssl_certificate /etc/letsencrypt/live/api.realms2riches.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.realms2riches.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Grafana dashboard
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    # Prometheus metrics API (for external scrapers)
    location /prometheus/ {
        proxy_pass http://localhost:9090/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    # Basic auth for monitoring (optional but recommended)
    auth_basic "Monitoring Access";
    auth_basic_user_file /etc/nginx/.htpasswd;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
}

# HTTPS Dashboard (frontend)
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name realms2riches.com www.realms2riches.com;

    ssl_certificate /etc/letsencrypt/live/api.realms2riches.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.realms2riches.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    root /var/www/swarmos/frontend/public;
    index index.html;

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass https://api.realms2riches.com/;
        proxy_ssl_verify off;
        proxy_set_header Host api.realms2riches.com;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
}
NGINX_CONFIG

echo "✅ Nginx config template created at /tmp/swarmos-ssl.conf"

# ===================================================================
# 4. DOCKER-COMPOSE DEPLOYMENT
# ===================================================================

echo "🚀 Starting production stack:"
echo "  docker compose -f docker-compose.yml up -d"
echo ""
echo "  Services:"
echo "    - Backend API:     http://localhost:8000"
echo "    - Prometheus:      http://localhost:9090"
echo "    - Grafana:         http://localhost:3000"
echo "    - Nginx Proxy:     http://localhost:80/443"

# ===================================================================
# 5. MONITOR & LOGS
# ===================================================================

echo ""
echo "📊 Monitoring commands:"
echo "  docker compose logs -f backend      # Backend logs"
echo "  docker compose logs -f prometheus   # Prometheus logs"
echo "  docker compose logs -f grafana      # Grafana logs"
echo "  docker compose ps                   # Container status"
echo "  docker compose stats                # Resource usage"

# ===================================================================
# 6. BACKUP & PERSISTENCE
# ===================================================================

echo ""
echo "💾 Data persistence:"
echo "  - PostgreSQL: monitoring/postgres_data (volume)"
echo "  - Redis: monitoring/redis_data (volume)"
echo "  - Prometheus: monitoring/prometheus_data (volume)"
echo "  - Grafana: monitoring/grafana_data (volume)"
echo ""
echo "  Backup:"
echo "    docker run --rm -v swarmenterprise-v2_postgres_data:/data alpine tar czf - /data > backup-pg.tar.gz"

# ===================================================================
# 7. ENDPOINTS AFTER DEPLOYMENT
# ===================================================================

echo ""
echo "📡 Production Endpoints:"
echo "  API:          https://api.realms2riches.com"
echo "  Health:       https://api.realms2riches.com/health"
echo "  Metrics:      https://api.realms2riches.com/metrics"
echo "  Grafana:      https://monitoring.realms2riches.com (admin/admin)"
echo "  Prometheus:   https://monitoring.realms2riches.com/prometheus"
echo "  Dashboard:    https://realms2riches.com"
