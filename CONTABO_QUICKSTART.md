# Brewery Manager - Contabo Quick Start

## Your Server Info

| Detail | Value |
|--------|-------|
| **IP Address** | `109.123.237.161` |
| **IPv6** | `2407:3640:2324:0351:0000:0000:0000:0001` |
| **Region** | Singapore |
| **OS** | Linux (Ubuntu) |
| **Plan** | Cloud VPS 20 SSD (200GB) |
| **Username** | `root` |
| **Auto Backup** | Enabled ✓ |

---

## Step 1: Connect to Your Server

```bash
ssh root@109.123.237.161
```

---

## Step 2: Update System

```bash
apt update && apt upgrade -y
```

---

## Step 3: Install Docker

```bash
# Remove old versions
apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null

# Install prerequisites
apt install -y ca-certificates curl gnupg

# Add Docker GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verify
docker --version
docker compose version
```

---

## Step 4: Upload Project from Your Laptop

### Option A: Using SCP (from your laptop terminal)

```bash
# From your laptop, in the directory containing brewery_manager
scp -r brewery_manager root@109.123.237.161:~/brewery-manager
```

### Option B: Using rsync (faster, can resume)

```bash
rsync -avz --progress brewery_manager/ root@109.123.237.161:~/brewery-manager/
```

### Option C: Zip & Upload (if large files)

```bash
# On your laptop - create zip
zip -r brewery-manager.zip brewery_manager/

# Upload
scp brewery-manager.zip root@109.123.237.161:~/

# On server - unzip
ssh root@109.123.237.161
cd ~
apt install -y unzip
unzip brewery-manager.zip -d brewery-manager
```

---

## Step 5: Configure & Launch

SSH into server:
```bash
ssh root@109.123.237.161
cd ~/brewery-manager
```

Configure environment:
```bash
cp .env.example .env

# Generate secret key
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Edit .env file:
```bash
nano .env
```

Set (paste the raw key, no brackets or dashes):
```
SECRET_KEY=a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890
FLASK_ENV=production
OPENAI_API_KEY=sk-...  # Optional
```

Example: If `python3 -c "import secrets; print(secrets.token_hex(32))"` outputs `abc123def456...`, then set:
```
SECRET_KEY=abc123def456...
```

Save: `Ctrl+X`, `Y`, `Enter`

Build and start:
```bash
docker compose up -d --build

# Verify it's running
docker compose ps
```

---

## Step 6: Open Firewall Ports

```bash
# Install UFW if not present
apt install -y ufw

# Allow ports
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp

# Enable firewall
ufw --force enable

# Check status
ufw status
```

---

## Step 7: Access Your App

Open in browser:
```
http://109.123.237.161
```

You should see the Brewery Manager login page!

---

## Step 8: Setup Domain & SSL (Optional)

### Point Domain to Server
In your DNS provider, add A record:
```
brewery.yourdomain.com → 109.123.237.161
```

### Get SSL Certificate
```bash
# Install certbot
apt install -y certbot python3-certbot-nginx

# Get certificate
certbot --nginx -d brewery.yourdomain.com

# Auto-renewal
systemctl enable certbot.timer
```

---

## Useful Commands

```bash
# View logs
docker compose logs -f

# Restart app
docker compose restart

# Stop app
docker compose down

# Update app (re-upload from laptop, then)
docker compose up -d --build

# Backup database
docker compose exec brewery-manager python -c "from utils.backup import create_backup; create_backup()"

# Enter container shell
docker compose exec brewery-manager bash
```

---

## Troubleshooting

### Check if app is running
```bash
curl http://localhost:5001
```

### View container status
```bash
docker compose ps
docker stats
```

### Check logs for errors
```bash
docker compose logs --tail=100 brewery-manager
```

### Restart everything
```bash
docker compose down
docker compose up -d --build
```

---

Your server specs are excellent for testing - 200GB disk gives plenty of room for database growth and backups!