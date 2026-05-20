#!/bin/bash
# Full deployment - copies all code + database to VPS
# Run from laptop: bash deploy_full.sh

VPS="root@109.123.237.161"
LOCAL_DIR="/Users/agastya/coding/agents/brewery_manager"
REMOTE_DIR="/opt/brewery_manager"

echo "=== Step 1: Kill old instance on VPS ==="
ssh $VPS "kill \$(pgrep -f 'run.py' | head -1) 2>/dev/null; echo done"

echo "=== Step 2: Backup VPS database ==="
ssh $VPS "cp $REMOTE_DIR/data/brewery.db /tmp/brewery_vps_backup.db 2>/dev/null; echo done"

echo "=== Step 3: Upload local database (real data) ==="
scp "$LOCAL_DIR/data/brewery.db" $VPS:$REMOTE_DIR/data/brewery.db

echo "=== Step 4: Upload all code files ==="
# Upload key Python files
scp "$LOCAL_DIR/web/app.py" $VPS:$REMOTE_DIR/web/app.py
scp "$LOCAL_DIR/models/database.py" $VPS:$REMOTE_DIR/models/database.py
scp "$LOCAL_DIR/utils/ai_tools.py" $VPS:$REMOTE_DIR/utils/ai_tools.py
scp "$LOCAL_DIR/run.py" $VPS:$REMOTE_DIR/run.py
scp "$LOCAL_DIR/requirements.txt" $VPS:$REMOTE_DIR/requirements.txt

# Upload templates
scp "$LOCAL_DIR/web/templates/"*.html $VPS:$REMOTE_DIR/web/templates/ 2>/dev/null

# Upload reports/traceability templates
ssh $VPS "mkdir -p $REMOTE_DIR/web/templates/reports $REMOTE_DIR/web/templates/traceability"
scp "$LOCAL_DIR/web/templates/reports/"*.html $VPS:$REMOTE_DIR/web/templates/reports/ 2>/dev/null
scp "$LOCAL_DIR/web/templates/traceability/"*.html $VPS:$REMOTE_DIR/web/templates/traceability/ 2>/dev/null

# Upload static files
scp "$LOCAL_DIR/web/static/"*.css $VPS:$REMOTE_DIR/web/static/ 2>/dev/null
scp "$LOCAL_DIR/web/static/"*.js $VPS:$REMOTE_DIR/web/static/ 2>/dev/null

# Upload all utils
scp "$LOCAL_DIR/utils/"*.py $VPS:$REMOTE_DIR/utils/ 2>/dev/null

echo "=== Step 5: Install requirements ==="
ssh $VPS "cd $REMOTE_DIR && source venv/bin/activate && pip install -r requirements.txt -q 2>&1 | tail -3"

echo "=== Step 6: Start the app ==="
ssh $VPS "cd $REMOTE_DIR && source venv/bin/activate && nohup python run.py --port 5001 > /tmp/brewery.log 2>&1 &"

sleep 3

echo "=== Step 7: Verify ==="
HTTP=$(ssh $VPS "curl -s -o /dev/null -w '%{http_code}' http://localhost:5001/")
echo "HTTP status: $HTTP"

if [ "$HTTP" = "200" ]; then
    echo "SUCCESS! App running with real data at http://109.123.237.161:5001"
else
    echo "ERROR - checking logs:"
    ssh $VPS "tail -10 /tmp/brewery.log"
fi

# Check quantum_edge untouched
QC=$(ssh $VPS "curl -s -o /dev/null -w '%{http_code}' http://localhost:80/")
echo "quantum_edge still running: HTTP $QC"