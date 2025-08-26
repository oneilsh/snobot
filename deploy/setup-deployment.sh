#!/bin/bash

# SNOBot Deployment Setup Script
# Run this script as root on a fresh Ubuntu server

set -e

echo "Setting up SNOBot deployment environment..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "This script must be run as root"
    exit 1
fi

# Update system
echo "Updating system packages..."
apt update
apt upgrade -y

# Install required packages
echo "Installing required packages..."
apt install -y nginx ufw python3-pip curl git

# Install uv
echo "Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"
ln -sf ~/.cargo/bin/uv /usr/local/bin/uv

# Create snobot user
echo "Creating snobot user..."
if ! id "snobot" &>/dev/null; then
    adduser --system --group --no-create-home snobot
    usermod -s /bin/bash snobot
fi

# Create directories
echo "Creating application directories..."
mkdir -p /opt/snobot
mkdir -p /etc/snobot
mkdir -p /var/log/snobot

# Set permissions
chown snobot:snobot /opt/snobot
chown root:snobot /etc/snobot
chown snobot:snobot /var/log/snobot
chmod 750 /opt/snobot
chmod 750 /etc/snobot
chmod 755 /var/log/snobot

echo "Deployment environment setup complete!"
echo "Next steps:"
echo "1. Copy your application files to /opt/snobot"
echo "2. Create /etc/snobot/.env with your configuration"
echo "3. Run the application setup"
