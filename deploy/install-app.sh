#!/bin/bash

# SNOBot Application Installation Script
# Run this from the project root directory after setup-deployment.sh

set -e

echo "Installing SNOBot application..."

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "Error: app.py not found. Run this script from the SNOBot project root."
    exit 1
fi

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "This script must be run as root"
    exit 1
fi

# Check if .env exists in current directory
if [ ! -f ".env" ]; then
    echo "Error: .env file not found in current directory."
    echo "Please create a .env file with OPENAI_API_KEY and (optional) ACCESS_PW"
    exit 1
fi

# Copy application files
echo "Copying application files..."
cp -r . /opt/snobot/
rm -f /opt/snobot/.env  # Remove any .env from the copy

# Move .env to secure location
echo "Setting up secure configuration..."
cp .env /etc/snobot/.env
chown root:snobot /etc/snobot/.env
chmod 640 /etc/snobot/.env

# Set proper ownership
chown -R snobot:snobot /opt/snobot
chmod -R 750 /opt/snobot

# Install dependencies as snobot user
echo "Installing Python dependencies..."
cd /opt/snobot
sudo -u snobot uv sync --no-install-project

echo "Application installation complete!"
