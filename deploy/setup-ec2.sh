#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Fiscalogix — EC2 First-Boot Setup Script
# Run once as ubuntu user after launching a fresh Ubuntu 22.04 t2.micro.
#
# Usage:
#   chmod +x setup-ec2.sh && ./setup-ec2.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e

echo "==> [1/6] System update"
sudo apt-get update -y && sudo apt-get upgrade -y

echo "==> [2/6] Install Docker"
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker ubuntu

echo "==> [3/6] Install certbot (free HTTPS)"
sudo apt-get install -y certbot

echo "==> [4/6] Create swap (prevents OOM on t2.micro with ML models)"
if [ ! -f /swapfile ]; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  echo "  Swap created: 2GB"
else
  echo "  Swap already exists, skipping."
fi

echo "==> [5/6] Create env file template"
sudo mkdir -p /etc/fiscalogix
if [ ! -f /etc/fiscalogix.env ]; then
  sudo tee /etc/fiscalogix.env > /dev/null <<'ENV'
# ── Database (RDS endpoint) ────────────────────────────────────────────────
DATABASE_URL=postgresql://admin:CHANGE_ME@YOUR-RDS-ENDPOINT:5432/fiscalogix

# ── Auth ───────────────────────────────────────────────────────────────────
JWT_SECRET_KEY=CHANGE_ME_use_openssl_rand_hex_32

# ── Redis (local container) ────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# ── External APIs ──────────────────────────────────────────────────────────
OPENWEATHER_API_KEY=CHANGE_ME
ACLED_API_KEY=CHANGE_ME
ACLED_EMAIL=CHANGE_ME
MARINETRAFFIC_API_KEY=CHANGE_ME
ENV
  sudo chmod 600 /etc/fiscalogix.env
  echo "  Created /etc/fiscalogix.env — EDIT THIS FILE before starting services."
else
  echo "  /etc/fiscalogix.env already exists, skipping."
fi

echo "==> [6/6] Clone repo (edit URL below)"
# Replace with your actual repo URL
# git clone https://github.com/YOUR_USERNAME/fiscalogix.git ~/fiscalogix

echo ""
echo "════════════════════════════════════════════════════════"
echo " Setup complete. Next steps:"
echo ""
echo " 1. Edit secrets:   sudo nano /etc/fiscalogix.env"
echo " 2. Clone your repo: git clone <your-repo> ~/fiscalogix"
echo " 3. Build & start:  cd ~/fiscalogix && docker compose -f docker-compose.prod.yml up -d --build"
echo " 4. Get SSL cert:   sudo certbot certonly --standalone -d yourdomain.com"
echo " 5. Check logs:     docker compose -f docker-compose.prod.yml logs -f"
echo "════════════════════════════════════════════════════════"
