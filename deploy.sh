#!/bin/bash
# Brewery Manager - Safe Deployment Script
# Run from your laptop terminal

VPS="root@109.123.237.161"
REMOTE_DIR="/opt/brewery_manager"

echo "=========================================="
echo "Brewery Manager Deployment"
echo "=========================================="

# Step 1: Kill the old instance
echo -e "\n[1/5] Killing old instance on port 5001..."
ssh $VPS "kill \$(pgrep -f 'run.py' | head -1) 2>/dev/null; sleep 2; echo 'Old process killed'"

# Step 2: Backup database
echo -e "\n[2/5] Backing up database..."
ssh $VPS "cp $REMOTE_DIR/data/brewery.db /tmp/brewery_backup_\$(date +%Y%m%d_%H%M%S).db 2>/dev/null; echo 'Backup created'"

# Step 3: Upload new code
echo -e "\n[3/5] Uploading new code..."
rsync -avz --progress \
    --exclude='venv' \
    --exclude='data' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='*.pyc' \
    --exclude='venv/' \
    --exclude='.DS_Store' \
    ./ $VPS:$REMOTE_DIR/

# Step 4: Install dependencies on server
echo -e "\n[4/5] Installing dependencies..."
ssh $VPS "cd $REMOTE_DIR && \
    python3 -m venv venv 2>/dev/null || true && \
    source venv/bin/activate && \
    pip install -r requirements.txt --quiet"

# Step 5: Start the new instance
echo -e "\n[5/5] Starting Brewery Manager on port 5001..."
ssh $VPS "cd $REMOTE_DIR && \
    source venv/bin/activate && \
    nohup python run.py --port 5001 > /tmp/brewery.log 2>&1 &"

sleep 3

# Verify
echo -e "\n[VERIFY] Checking if app is running..."
HTTP_CODE=$(ssh $VPS "curl -s -o /dev/null -w '%{http_code}' http://localhost:5001/")
if [ "$HTTP_CODE" = "200" ]; then
    echo "SUCCESS! Brewery Manager is running on port 5001"
    echo "Access at: http://109.123.237.161:5001"
else
    echo "WARNING: Got HTTP $HTTP_CODE - checking logs..."
    ssh $VPS "tail -20 /tmp/brewery.log"
fi

# Verify quantum_edge is untouched
QC=$(ssh $VPS "curl -s -o /dev/null -w '%{http_code}' http://localhost:80/")
echo "quantum_edge on port 80: HTTP $QC (should be 200)"

echo -e "\n=========================================="
echo "Deployment complete!"
echo "=========================================="