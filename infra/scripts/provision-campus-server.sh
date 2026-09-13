#!/bin/bash
# Campus Local Server Provisioning Script (Debian / Ubuntu Server)
set -euo pipefail

echo "======================================================================"
echo "Digital Student Attendance System — Campus Host Provisioning"
echo "======================================================================"

# Update apt repositories
sudo apt-get update
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    ufw

# Install Docker Engine if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker Engine..."
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

# Configure Campus Firewall (UFW)
echo "Configuring firewall rules..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH Administration'
sudo ufw allow 80/tcp comment 'HTTP Gateway'
sudo ufw allow 443/tcp comment 'HTTPS Gateway'
sudo ufw --force enable

echo "Host provisioning complete. You can now deploy via docker compose."
