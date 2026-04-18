# GitHub Setup & Contabo Deployment Guide

## Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `brewery_manager`
3. Description: "Brewery Management System with AI features"
4. Keep it **Public** or **Private** (your choice)
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

## Step 2: Push Code to GitHub

Run these commands in your terminal:

```bash
cd /Users/agastya/coding/agents

# Add GitHub as remote
git remote add origin https://github.com/artbyagastya-hub/brewery_manager.git

# Rename branch to main (GitHub standard)
git branch -M main

# Push to GitHub
git push -u origin main
```

## Step 3: Deploy on Contabo VPS

SSH into your Contabo VPS and run:

```bash
# Clone your repository
cd /opt
git clone https://github.com/artbyagastya-hub/brewery_manager.git
cd brewery_manager

# Create environment file
cp .env.example .env
nano .env  # Edit with your actual values

# Install dependencies
pip install -r requirements.txt

# Initialize database with seed data
python seed_data.py

# Run the application
python run.py
```

## Step 4: Future Updates

When you make changes locally:

```bash
# On your laptop
cd /Users/agastya/coding/agents
git add brewery_manager/
git commit -m "Your change description"
git push origin main
```

Then on your VPS:

```bash
cd /opt/brewery_manager
git pull origin main
# Restart your application
```

## Using Docker on Contabo (Recommended)

```bash
cd /opt/brewery_manager
cp .env.example .env
nano .env
docker-compose up -d --build
docker-compose logs -f