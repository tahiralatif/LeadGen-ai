#!/bin/bash
# Setup SSL for leadgen.14.jugaar.ai

echo "Setting up SSL for leadgen.14.jugaar.ai..."

# Get SSL certificate
certbot certonly --webroot -w /var/www/leadgen -d leadgen.14.jugaar.ai --non-interactive --agree-tos --email tahira@jugaar.ai

# Update Nginx config with SSL
cat > /etc/nginx/sites-available/leadgen << 'EOF'
server {
    listen 80;
    server_name leadgen.14.jugaar.ai;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name leadgen.14.jugaar.ai;

    ssl_certificate /etc/letsencrypt/live/leadgen.14.jugaar.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/leadgen.14.jugaar.ai/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    location /api/track/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# Reload Nginx
nginx -t && systemctl reload nginx

echo "SSL setup complete!"
echo "Your site is now available at: https://leadgen.14.jugaar.ai"