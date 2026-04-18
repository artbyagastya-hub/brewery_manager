# Git Workflow & VPS Update Guide

## Repository Info
- **GitHub:** https://github.com/agastyanos/Brewery-Manager
- **VPS:** Contabo - `root@109.123.237.161`
- **App URL:** http://109.123.237.161:5001

---

## From Your Laptop (Making Changes)

### 1. Pull latest changes first
```bash
cd /Users/agastya/coding/agents/brewery_manager
git pull origin main
```

### 2. Make your changes (edit files, add features, fix bugs)

### 3. Stage and commit
```bash
git add .
git commit -m "Describe what you changed"
git push origin main
```

---

## On Contabo VPS (Deploy Updates)

### SSH into your VPS
```bash
ssh root@109.123.237.161
```

### Pull and restart
```bash
cd /opt/brewery_manager
git pull origin main
source venv/bin/activate

# Restart the app
pkill -9 -f "python run.py"
nohup python run.py > /var/log/brewery.log 2>&1 &
```

### If new Python packages were added
```bash
cd /opt/brewery_manager
source venv/bin/activate
pip install -r requirements.txt
pkill -9 -f "python run.py"
nohup python run.py > /var/log/brewery.log 2>&1 &
```

---

## Quick Commands Cheat Sheet

| Action | Command |
|--------|---------|
| Push to GitHub | `git add . && git commit -m "msg" && git push` |
| Pull from GitHub | `git pull origin main` |
| Start app on VPS | `nohup python run.py > /var/log/brewery.log 2>&1 &` |
| Stop app on VPS | `pkill -9 -f "python run.py"` |
| View logs | `cat /var/log/brewery.log` |
| Check if running | `ps aux \| grep python` |

---

## After VPS Reboot

```bash
ssh root@109.123.237.161
cd /opt/brewery_manager
source venv/bin/activate
nohup python run.py > /var/log/brewery.log 2>&1 &
```

---

## Notes
- Always `git pull` before making changes on your laptop
- Always `git pull` on VPS after pushing changes
- The database (`data/brewery.db`) is NOT in git - each environment has its own
- The `.env` file is NOT in git - keep secrets local