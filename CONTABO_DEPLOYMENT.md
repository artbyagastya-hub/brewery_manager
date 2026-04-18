# Contabo VPS Deployment Guide - Brewery Manager

## VPS Selection

### Recommended: Cloud VPS S (~€6.99/month)

| Spec | Value |
|------|-------|
| **CPU** | 4 vCPU AMD |
| **RAM** | 8 GB |
| **Storage** | 50 GB SSD |
| **Bandwidth** | Unlimited |
| **Location** | Singapore or EU (closest to users) |
| **OS** | Ubuntu 24.04 LTS |

> More than sufficient for testing with multiple users.

### VPS Settings in Contabo Panel

- **Operating System**: Ubuntu 24.04 LTS
- **Enable automatic backups**: Recommended for production
- **SSH Key**: Upload your public key for secure access
- **Hostname**: `brewery-manager` (or your preference)

---

## Step 1: Initial Server Setup

### 1.1 Connect via SSH

```bash
ssh root@YOUR_SERVER_IP
```

### 1.2 Update System

```bash
apt update && apt upgrade -y
```

### 1.3 Create Non-Root User (Recommended)

```bash
# Create user
adduser brewery

# Add to sudo group
usermod -aG sudo brewery

# Add SSH key for new user
mkdir -p /home/brewery/.ssh
cp ~/.ssh/authorized_keys /home/brewery/.ssh/
chown -R brewery:brewery /home/brewery/.ssh
chmod 700 /home/brewery/.ssh
chmod 600 /home/brewery/.ssh/authorized_keys

# Switch to new user
su - brewery
```

### 1.4 Configure SSH Security

```bash
sudo nano /etc/ssh/sshd_config
```

Change these settings:
```
PermitRootLogin no
PasswordAuthentication no
Port 2222  # Optional: change default SSH port
```

```bash
sudo systemctl restart sshd
```

---

## Step 2: Install Docker & Docker Compose

### 2.1 Install Docker

```bash
# Remove old versions
sudo apt remove -y docker docker-engine docker.io containerd runc

# Install prerequisites
sudo apt install -y ca-certificates curl gnupg

# Add Docker GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 2.2 Add User to Docker Group

```bash
sudo usermod -aG docker $USER
newgrp docker
```

### 2.3 Verify Installation

```bash
docker --version
docker compose version
```

---

## Step 3: Deploy Brewery Manager

### 3.1 Clone Repository

```bash
cd ~
git clone YOUR_REPO_URL brewery-manager
cd brewery-manager
```

### 3.2 Configure Environment

```bash
cp .env.example .env
nano .env
```

Set these variables:
```env
SECRET_KEY=your-very-long-random-secret-key-here
OPENAI_API_KEY=sk-...        # Optional: for AI features
FLASK_ENV=production
```

Generate a strong secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3.3 Build and Start

```bash
docker compose up -d --build
```

### 3.4 Verify Running

```bash
docker compose ps
docker compose logs -f brewery-manager
```

---

## Step 4: Configure Firewall

### 4.1 Install UFW

```bash
sudo apt install -y ufw
```

### 4.2 Configure Rules

```bash
# Allow SSH (use your port if changed)
sudo ufw allow 2222/tcp  # If you changed SSH port
sudo ufw allow 22/tcp    # Default SSH port

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

---

## Step 5: Setup SSL with Let's Encrypt

### 5.1 Point Domain to Server

In your DNS provider, add an A record:
```
brewery.yourdomain.com → YOUR_SERVER_IP
```

### 5.2 Modify docker-compose.yml

```yaml
services:
  nginx:
    image: nginx:alpine
    container_name: brewery-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./ssl:/etc/nginx/ssl:ro
      - certbot-etc:/etc/letsencrypt
      - certbot-var:/var/lib/letsencrypt
    depends_on:
      - brewery-manager
    networks:
      - brewery-network

  certbot:
    image: certbot/certbot
    container_name: certbot
    volumes:
      - certbot-etc:/etc/letsencrypt
      - certbot-var:/var/lib/letsencrypt
      - ./ssl:/ssl
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done'"

volumes:
  certbot-etc:
  certbot-var:
```

### 5.3 Initial Certificate Request

```bash
docker compose run --rm certbot certonly --webroot --webroot-path=/var/www/certbot -d brewery.yourdomain.com
```

### 5.4 Update nginx.conf

Uncomment the HTTPS section and update:
```nginx
server {
    listen 443 ssl http2;
    server_name brewery.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/brewery.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/brewery.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://brewery_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /socket.io {
        proxy_pass http://brewery_app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        proxy_pass http://brewery_app;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}

server {
    listen 80;
    server_name brewery.yourdomain.com;
    return 301 https://$host$request_uri;
}
```

### 5.5 Restart with SSL

```bash
docker compose down
docker compose up -d
```

---

## Step 6: Automated Backups

### 6.1 Create Backup Script

```bash
sudo nano /usr/local/bin/backup-brewery.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/brewery/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Run backup via Docker
cd /home/brewery/brewery-manager
docker compose exec -T brewery-manager python -c "from utils.backup import create_backup; create_backup()"

# Copy backup from volume
docker compose cp brewery-manager:/app/backups/. $BACKUP_DIR/

# Keep only last 7 days
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

### 6.2 Schedule Daily Backups

```bash
sudo chmod +x /usr/local/bin/backup-brewery.sh
crontab -e
```

Add:
```
0 3 * * * /usr/local/bin/backup-brewery.sh >> /var/log/brewery-backup.log 2>&1
```

---

## Step 7: Monitoring

### 7.1 Check Application Status

```bash
# Container status
docker compose ps

# Logs
docker compose logs -f brewery-manager

# Resource usage
docker stats
```

### 7.2 Health Check Script

```bash
nano ~/health-check.sh
```

```bash
#!/bin/bash
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/)
if [ $response -ne 200 ]; then
    echo "Brewery Manager is DOWN! Restarting..."
    cd /home/brewery/brewery-manager
    docker compose restart
fi
```

```bash
chmod +x ~/health-check.sh
crontab -e
```

Add (check every 5 minutes):
```
*/5 * * * * /home/brewery/health-check.sh >> /var/log/health-check.log 2>&1
```

---

## Quick Reference Commands

| Action | Command |
|--------|---------|
| **Start** | `docker compose up -d` |
| **Stop** | `docker compose down` |
| **Restart** | `docker compose restart` |
| **View logs** | `docker compose logs -f` |
| **Rebuild** | `docker compose up -d --build` |
| **Database backup** | `docker compose exec brewery-manager python -c "from utils.backup import create_backup; create_backup()"` |
| **Shell access** | `docker compose exec brewery-manager bash` |
| **Update app** | `git pull && docker compose up -d --build` |

---

## Troubleshooting

### Port 5001 already in use
```bash
sudo lsof -i :5001
sudo kill -9 <PID>
```

### Database locked errors
```bash
docker compose restart brewery-manager
```

### SSL renewal failing
```bash
docker compose run --rm certbot renew --force-renewal
docker compose restart nginx
```

### Out of disk space
```bash
# Clean Docker
docker system prune -a
docker volume prune
```

---

## Cost Summary (Cloud VPS S)

| Item | Cost |
|------|------|
| VPS S (monthly) | ~€6.99 |
| Domain (optional) | ~€10/year |
| SSL (Let's Encrypt) | Free |
| **Total** | **~€7/month** |

Perfect for testing and small-scale production!