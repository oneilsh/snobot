#!/bin/bash

# SNOBot Service Configuration Script
# Run this after install-app.sh

set -e

echo "Configuring SNOBot services..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "This script must be run as root"
    exit 1
fi

# Install systemd service
echo "Installing systemd service..."
cp deploy/snobot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable snobot

# Configure nginx
echo "Configuring nginx..."
cp deploy/nginx-snobot /etc/nginx/sites-available/snobot
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/snobot /etc/nginx/sites-enabled/

# Test nginx configuration
nginx -t

# Configure firewall
echo "Configuring firewall..."
ufw allow ssh
ufw allow 'Nginx Full'
ufw --force enable

# Set up log rotation
echo "Setting up log rotation..."
cat > /etc/logrotate.d/snobot << EOF
/var/log/snobot/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 snobot snobot
    postrotate
        systemctl reload snobot
    endscript
}
EOF

echo "Service configuration complete!"
echo "Starting services..."

# Start services
systemctl start snobot
systemctl reload nginx

echo "Deployment complete!"
echo "SNOBot should now be available at http://your-server-ip"
echo ""
echo "Useful commands:"
echo "  systemctl status snobot    # Check service status"
echo "  systemctl restart snobot   # Restart application"
echo "  tail -f /var/log/snobot/snobot.log  # View application logs"
echo "  journalctl -u snobot -f    # View systemd logs"
