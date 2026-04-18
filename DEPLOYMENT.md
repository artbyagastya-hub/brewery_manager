# Brewery Manager Deployment Guide

## Overview

Brewery Manager is a Flask-based web application with:
- **Backend**: Python 3.11 + Flask + Socket.IO
- **Database**: SQLite (file-based)
- **Real-time**: WebSocket support via Flask-SocketIO
- **AI Features**: OpenAI integration
- **Cache/Queue**: Redis (optional)

---

## Deployment Options

### Option 1: Docker Compose (Recommended)

**Best for**: Production deployments, VPS/dedicated servers

#### Prerequisites
- Docker & Docker Compose installed
- Domain name (optional but recommended)
- SSL certificates (for HTTPS)

#### Quick Start

```bash
# 1. Clone the repository
cd brewery_manager

# 2. Create environment file
cp .env.example .env
# Edit .env and set:
#   - SECRET_KEY (generate a random string)
#   - OPENAI_API_KEY (if using AI features)

# 3. Build and start
docker-compose up -d

# 4. Access the application
# HTTP: http://your-server-ip
```

#### With SSL/HTTPS

```bash
# 1. Create SSL directory
mkdir -p ssl

# 2. Add your SSL certificates
cp /path/to/cert.pem ssl/
cp /path/to/key.pem ssl/

# 3. Uncomment HTTPS section in nginx.conf

# 4. Restart
docker-compose down
docker-compose up -d
```

---

### Option 2: Direct Python Deployment

**Best for**: Development, small-scale production

#### Prerequisites
- Python 3.11+
- pip

#### Steps

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
export SECRET_KEY="your-secret-key-here"
export OPENAI_API_KEY="sk-..."  # Optional

# 4. Run the application
python run.py
```

The app will be available at `http://localhost:5001`

---

### Option 3: Cloud Platforms

#### A. Railway.app

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login and deploy
railway login
railway init
railway up
```

#### B. Render.com

1. Connect your GitHub repository
2. Create a new Web Service
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python run.py`
5. Add environment variables in dashboard

#### C. DigitalOcean App Platform

1. Create new app from GitHub
2. Select Python environment
3. Set run command: `python run.py`
4. Add environment variables

#### D. AWS (EC2 + Docker)

```bash
# On EC2 instance
sudo yum update -y
sudo yum install docker -y
sudo service docker start
sudo usermod -a -G docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Deploy
git clone <your-repo>
cd brewery_manager
docker-compose up -d
```

#### E. Google Cloud Run

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/PROJECT-ID/brewery-manager

# Deploy
gcloud run deploy brewery-manager \
  --image gcr.io/PROJECT-ID/brewery-manager \
  --platform managed \
  --port 5001 \
  --set-env-vars SECRET_KEY=your-secret-key
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Flask secret key for sessions |
| `OPENAI_API_KEY` | No | OpenAI API key for AI features |
| `FLASK_ENV` | No | `production` or `development` |

---

## Database Persistence

### Docker Volumes
The docker-compose setup uses named volumes:
- `brewery-data`: SQLite database storage
- `brewery-backups`: Backup files

### Backup Database

```bash
# Docker
docker exec brewery-manager python -c "from utils.backup import create_backup; create_backup()"

# Or use the web interface at /backup
```

---

## Performance Considerations

### Current Setup
- SQLite suitable for small to medium workloads
- Single-worker Flask process
- In-memory session storage

### Scaling Recommendations

For higher traffic:

1. **Switch to PostgreSQL**:
   ```python
   # Update requirements.txt
   psycopg2-binary==2.9.9
   SQLAlchemy==2.0.23
   ```

2. **Use Gunicorn with multiple workers**:
   ```bash
   gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5001 run:app
   ```

3. **Add Redis for sessions**:
   ```python
   SESSION_TYPE = 'redis'
   SESSION_REDIS = 'redis://redis:6379'
   ```

---

## Monitoring

### Health Check Endpoint
The application should expose a health check (you may want to add):

```python
@app.route('/health')
def health():
    return {'status': 'healthy'}
```

### Logs

```bash
# Docker logs
docker-compose logs -f brewery-manager

# System logs (direct deployment)
journalctl -u brewery-manager -f
```

---

## Security Checklist

- [ ] Set strong `SECRET_KEY`
- [ ] Enable HTTPS in production
- [ ] Configure firewall rules
- [ ] Set up regular database backups
- [ ] Review and update dependencies regularly
- [ ] Enable rate limiting (already configured via Flask-Limiter)

---

## Troubleshooting

### Port already in use
```bash
# Find process using port 5001
lsof -i :5001
# Kill it
kill -9 <PID>
```

### Database locked errors
- Ensure only one application instance accesses SQLite
- Consider switching to PostgreSQL for multi-instance deployments

### WebSocket connection issues
- Ensure nginx proxy passes WebSocket headers
- Check firewall allows WebSocket connections

---

## Support

For issues or questions, refer to:
- `README.md` - General documentation
- `SECURITY.md` - Security guidelines
- `PERFORMANCE.md` - Performance optimization