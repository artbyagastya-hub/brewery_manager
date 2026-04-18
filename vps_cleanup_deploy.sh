#!/bin/bash
# VPS Cleanup and Fresh Deploy Script
# Run this on your Contabo VPS

echo "=== Brewery Manager VPS Cleanup & Deploy ==="

# Stop any running services
echo "Stopping existing services..."
pkill -f "python run.py" 2>/dev/null || true
pkill -f "gunicorn" 2>/dev/null || true

# If using Docker
if command -v docker-compose &> /dev/null; then
    echo "Stopping Docker containers..."
    cd /opt/brewery_manager 2>/dev/null && docker-compose down 2>/dev/null || true
fi

# Backup old database if it exists
echo "Backing up old database..."
if [ -f "/opt/brewery_manager/data/brewery.db" ]; then
    mkdir -p /opt/brewery_backup
    cp /opt/brewery_manager/data/brewery.db /opt/brewery_backup/brewery_backup_$(date +%Y%m%d_%H%M%S).db
    echo "Database backed up to /opt/brewery_backup/"
fi

# Remove old installation
echo "Removing old files..."
rm -rf /opt/brewery_manager

# Clone fresh from GitHub
echo "Cloning from GitHub..."
cd /opt
git clone https://github.com/artbyagastya-hub/brewery_manager.git
cd brewery_manager

# Setup environment
echo "Setting up environment..."
cp .env.example .env
echo ""
echo "=== IMPORTANT ==="
echo "Edit .env file with your settings:"
echo "  nano /opt/brewery_manager/.env"
echo ""
echo "Set these values:"
echo "  SECRET_KEY=your-secret-key-here"
echo "  MIMO_API_KEY=your-mimo-api-key-here"
echo ""
echo "Press Enter to continue after editing .env..."
read

# Restore database backup if exists
LATEST_BACKUP=$(ls -t /opt/brewery_backup/brewery_backup_*.db 2>/dev/null | head -1)
if [ -n "$LATEST_BACKUP" ]; then
    echo "Restoring database from backup..."
    mkdir -p /opt/brewery_manager/data
    cp "$LATEST_BACKUP" /opt/brewery_manager/data/brewery.db
    echo "Database restored!"
else
    echo "No backup found. Run 'python seed_data.py' to create fresh database."
fi

echo ""
echo "=== Deploy Options ==="
echo "1. Run with Python directly:"
echo "   cd /opt/brewery_manager"
echo "   pip install -r requirements.txt"
echo "   python seed_data.py  # Only if fresh database"
echo "   python run.py"
echo ""
echo "2. Run with Docker (recommended):"
echo "   cd /opt/brewery_manager"
echo "   docker-compose up -d --build"
echo ""
echo "=== Cleanup Complete ==="