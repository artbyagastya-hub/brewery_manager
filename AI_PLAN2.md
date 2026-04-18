# AI_PLAN2.md - Implementation & Recovery Guide

## 📌 Purpose
This document provides step-by-step instructions for implementing, testing, and recovering the AI system. Follow each section sequentially and verify at each checkpoint.

---

## 🔧 Pre-Implementation Checklist

### 1. Backup Current State
```bash
cd /Users/agastya/coding/agents/brewery_manager

# Create timestamped backup
BACKUP_DIR="backups/ai_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup critical files
cp -r utils/ai_*.py "$BACKUP_DIR/"
cp -r utils/mimo_engine.py "$BACKUP_DIR/"
cp -r utils/agent.py "$BACKUP_DIR/"
cp -r utils/scheduler.py "$BACKUP_DIR/"
cp web/app.py "$BACKUP_DIR/"
cp models/database.py "$BACKUP_DIR/"

# Backup database
cp data/brewery.db "$BACKUP_DIR/"

echo "✅ Backup created at: $BACKUP_DIR"
```

### 2. Verify Environment
```bash
# Check Python version (requires 3.9+)
python3 --version

# Check required packages
pip3 list | grep -E "flask|aiohttp|apscheduler"

# Verify database exists
ls -la data/brewery.db

# Check .env file exists
cat .env | grep -E "MIMO_API_KEY|SECRET_KEY"
```

### 3. Install Missing Dependencies (if needed)
```bash
pip3 install flask flask-wtf flask-limiter flask-talisman aiohttp apscheduler
```

---

## 📋 Phase 1: Core Engine Setup

### Step 1.1: MIMO Engine (`utils/mimo_engine.py`)

**Status Check:**
```bash
python3 -c "from utils.mimo_engine import get_engine; print('✅ MIMO Engine OK')"
```

**If broken, restore:**
```python
# utils/mimo_engine.py - Core structure
import aiohttp
import asyncio
from typing import Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class MIMOEngine:
    def __init__(self):
        self.api_key = os.getenv('MIMO_API_KEY')
        self.api_url = os.getenv('MIMO_API_URL', 'https://api.mimo.ai/v1')
        self.conversation_history = {}
    
    async def process_message(self, message: str, context: dict = None) -> dict:
        """Process message through MiMo API"""
        try:
            # Implementation here
            return {'content': 'Response', 'status': 'success'}
        except Exception as e:
            return {'content': f'Error: {str(e)}', 'status': 'error'}
    
    def clear_history(self, session_id: str):
        """Clear conversation history for session"""
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]
    
    def health_check(self) -> dict:
        """Check engine health"""
        return {
            'status': 'healthy',
            'api_configured': bool(self.api_key),
            'api_url': self.api_url
        }

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = MIMOEngine()
    return _engine
```

**Debug - Engine Connection Issues:**
```bash
# Test API connectivity
python3 -c "
from utils.mimo_engine import get_engine
engine = get_engine()
print(engine.health_check())
"

# Check API key
echo $MIMO_API_KEY

# Test with curl
curl -H "Authorization: Bearer $MIMO_API_KEY" https://api.mimo.ai/v1/health
```

### Step 1.2: Memory System (`utils/ai_memory.py`)

**Status Check:**
```bash
python3 -c "from utils.ai_memory import get_memory; print('✅ AI Memory OK')"
```

**If broken, verify database tables exist:**
```bash
sqlite3 data/brewery.db ".tables" | grep ai_memory
```

**If missing, create tables:**
```sql
sqlite3 data/brewery.db << 'EOF'
CREATE TABLE IF NOT EXISTS ai_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    context TEXT,
    action_taken TEXT,
    outcome TEXT,
    impact_score REAL,
    lesson_learned TEXT
);

CREATE INDEX IF NOT EXISTS idx_ai_memory_timestamp ON ai_memory(timestamp);
CREATE INDEX IF NOT EXISTS idx_ai_memory_event_type ON ai_memory(event_type);
EOF
```

**Debug - Memory Issues:**
```bash
# Check if ai_memory.py exists and is valid
python3 -c "
try:
    from utils.ai_memory import AIMemory
    memory = AIMemory()
    print('✅ Memory class loads OK')
    print(f'DB Path: {memory.db_path}')
except Exception as e:
    print(f'❌ Error: {e}')
"

# Test memory storage
python3 -c "
from utils.ai_memory import get_memory
memory = get_memory()
result = memory.store_event('test', {'msg': 'test'}, 'test action', 'success', 1.0)
print(f'Store result: {result}')
"
```

---

## 📋 Phase 2: Tools & Integration

### Step 2.1: AI Tools (`utils/ai_tools.py`)

**Status Check:**
```bash
python3 -c "from utils.ai_tools import get_tools; tools = get_tools(); print(f'✅ {len(tools)} tools loaded')"
```

**Debug - Import Errors:**
```bash
# Check for syntax errors
python3 -m py_compile utils/ai_tools.py && echo "✅ Syntax OK" || echo "❌ Syntax Error"

# Check imports
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from utils.ai_tools import get_tools, execute_tool
    print('✅ Imports OK')
except ImportError as e:
    print(f'❌ Import Error: {e}')
"
```

**If broken, minimal working version:**
```python
# utils/ai_tools.py - Minimal structure
from typing import Dict, List, Callable

class AITools:
    def __init__(self):
        self.tools = {}
    
    def register_tool(self, name: str, func: Callable, description: str):
        self.tools[name] = {'function': func, 'description': description}
    
    def get_tool_list(self) -> List[Dict]:
        return [{'name': k, 'description': v['description']} for k, v in self.tools.items()]
    
    def execute_tool(self, name: str, params: dict) -> dict:
        if name not in self.tools:
            return {'status': 'error', 'message': f'Tool {name} not found'}
        try:
            result = self.tools[name]['function'](**params)
            return {'status': 'success', 'result': result}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

_tools = None

def get_tools():
    global _tools
    if _tools is None:
        _tools = AITools()
    return _tools

def execute_tool(name: str, params: dict) -> dict:
    return get_tools().execute_tool(name, params)
```

### Step 2.2: Web Integration (`web/app.py`)

**Status Check:**
```bash
python3 -c "from web.app import app; print('✅ Flask app loads OK')"
```

**Debug - Import Chain Issues:**
```bash
# Check all AI-related imports
python3 -c "
import sys
sys.path.insert(0, '.')

modules_to_check = [
    'utils.mimo_engine',
    'utils.ai_memory', 
    'utils.ai_tools',
    'utils.ai_prompts',
    'utils.ai_planner',
    'utils.scheduler',
    'utils.agent'
]

for module in modules_to_check:
    try:
        __import__(module)
        print(f'✅ {module}')
    except Exception as e:
        print(f'❌ {module}: {e}')
"
```

**If app.py is broken, verify these critical sections exist:**
```python
# Required imports in web/app.py
from utils.mimo_engine import get_engine
from utils.ai_tools import get_tools, execute_tool
from utils.ai_prompts import get_system_prompt

# Required route
@app.route('/ai/chat', methods=['POST'])
@login_required
def ai_chat():
    # Implementation
    pass

# Required route for health check
@app.route('/ai/health')
def ai_health():
    engine = get_engine()
    return jsonify(engine.health_check())
```

---

## 📋 Phase 3: Planning System

### Step 3.1: AI Planner (`utils/ai_planner.py`)

**Status Check:**
```bash
python3 -c "from utils.ai_planner import get_planner; print('✅ AI Planner OK')"
```

**Debug - Database Issues:**
```bash
# Check planner tables exist
sqlite3 data/brewery.db "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'ai_plan%';"
```

**If missing, create tables:**
```sql
sqlite3 data/brewery.db << 'EOF'
CREATE TABLE IF NOT EXISTS ai_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_type TEXT NOT NULL,
    goal_description TEXT,
    status TEXT DEFAULT 'active',
    priority INTEGER DEFAULT 5,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    outcome TEXT,
    impact_score REAL
);

CREATE TABLE IF NOT EXISTS ai_plan_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER REFERENCES ai_plans(id),
    task_description TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    scheduled_at DATETIME,
    completed_at DATETIME,
    result TEXT,
    tool_used TEXT
);

CREATE INDEX IF NOT EXISTS idx_ai_plans_status ON ai_plans(status);
CREATE INDEX IF NOT EXISTS idx_ai_plan_tasks_plan_id ON ai_plan_tasks(plan_id);
EOF
```

### Step 3.2: Scheduler (`utils/scheduler.py`)

**Status Check:**
```bash
python3 -c "from utils.scheduler import get_scheduler; print('✅ Scheduler OK')"
```

**Debug - APScheduler Issues:**
```bash
# Check if APScheduler is installed
pip3 list | grep apscheduler

# If missing
pip3 install apscheduler

# Test scheduler initialization
python3 -c "
from utils.scheduler import get_scheduler
scheduler = get_scheduler()
print(f'Scheduler status: {scheduler}')
print(f'Jobs: {scheduler.get_jobs() if hasattr(scheduler, \"get_jobs\") else \"N/A\"}')
"
```

---

## 🚨 Emergency Recovery

### Quick Fix Script
```bash
#!/bin/bash
# Save as: fix_ai_system.sh

cd /Users/agastya/coding/agents/brewery_manager

echo "🔧 AI System Recovery Script"
echo "============================"

# 1. Check Python syntax for all AI files
echo "1. Checking syntax..."
for file in utils/ai_*.py utils/mimo_engine.py utils/agent.py utils/scheduler.py; do
    if [ -f "$file" ]; then
        python3 -m py_compile "$file" 2>&1 && echo "  ✅ $file" || echo "  ❌ $file - SYNTAX ERROR"
    fi
done

# 2. Verify database tables
echo "2. Checking database tables..."
REQUIRED_TABLES="ai_memory ai_plans ai_plan_tasks ai_scheduled_improvements ai_config brewery_goals ai_activity_log goals"
for table in $REQUIRED_TABLES; do
    EXISTS=$(sqlite3 data/brewery.db "SELECT name FROM sqlite_master WHERE type='table' AND name='$table';")
    if [ "$EXISTS" = "$table" ]; then
        echo "  ✅ Table: $table"
    else
        echo "  ❌ Missing table: $table"
    fi
done

# 3. Test imports
echo "3. Testing imports..."
python3 -c "
import sys
sys.path.insert(0, '.')
modules = ['utils.mimo_engine', 'utils.ai_memory', 'utils.ai_tools', 'utils.ai_prompts', 'utils.ai_planner', 'utils.scheduler']
for m in modules:
    try:
        __import__(m)
        print(f'  ✅ {m}')
    except Exception as e:
        print(f'  ❌ {m}: {e}')
"

# 4. Check environment variables
echo "4. Checking environment..."
if [ -f .env ]; then
    echo "  ✅ .env exists"
    grep -q "MIMO_API_KEY" .env && echo "  ✅ MIMO_API_KEY set" || echo "  ⚠️  MIMO_API_KEY missing"
    grep -q "SECRET_KEY" .env && echo "  ✅ SECRET_KEY set" || echo "  ⚠️  SECRET_KEY missing"
else
    echo "  ❌ .env missing"
fi

echo "============================"
echo "Recovery complete. Review any ❌ items above."
```

### Database Reset (Nuclear Option)
```bash
# WARNING: This will reset AI tables only, preserving brewery data
cd /Users/agastya/coding/agents/brewery_manager

# Backup first
cp data/brewery.db "data/brewery_before_reset_$(date +%Y%m%d_%H%M%S).db"

# Drop and recreate AI tables
sqlite3 data/brewery.db << 'EOF'
-- Drop AI tables
DROP TABLE IF EXISTS ai_memory;
DROP TABLE IF EXISTS ai_plan_tasks;
DROP TABLE IF EXISTS ai_plans;
DROP TABLE IF EXISTS ai_scheduled_improvements;
DROP TABLE IF EXISTS ai_config;
DROP TABLE IF EXISTS ai_activity_log;

-- Recreate
CREATE TABLE ai_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    context TEXT,
    action_taken TEXT,
    outcome TEXT,
    impact_score REAL,
    lesson_learned TEXT
);

CREATE TABLE ai_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_type TEXT NOT NULL,
    goal_description TEXT,
    status TEXT DEFAULT 'active',
    priority INTEGER DEFAULT 5,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    outcome TEXT,
    impact_score REAL
);

CREATE TABLE ai_plan_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER REFERENCES ai_plans(id),
    task_description TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    scheduled_at DATETIME,
    completed_at DATETIME,
    result TEXT,
    tool_used TEXT
);

CREATE TABLE ai_scheduled_improvements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    improvement_type TEXT NOT NULL,
    description TEXT,
    schedule_cron TEXT,
    last_run DATETIME,
    next_run DATETIME,
    status TEXT DEFAULT 'active',
    config TEXT
);

CREATE TABLE ai_config (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ai_activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    activity_type TEXT NOT NULL,
    description TEXT,
    triggered_by TEXT,
    result TEXT,
    impact TEXT
);

-- Insert default config
INSERT OR IGNORE INTO ai_config (key, value) VALUES 
    ('autonomy_level', 'suggester'),
    ('proactive_enabled', 'true'),
    ('daily_optimization', 'true');
EOF

echo "✅ AI tables reset complete"
```

### Service Restart
```bash
cd /Users/agastya/coding/agents/brewery_manager

# Kill any running Flask processes
pkill -f "python.*run.py" || true

# Clear Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Restart the application
python3 run.py &
sleep 3

# Verify it's running
curl -s http://localhost:5000/ai/health || echo "⚠️  Server may still be starting..."
```

---

## ✅ Verification Checklist

### After Each Phase, Run These Tests:

```bash
cd /Users/agastya/coding/agents/brewery_manager

echo "=== AI System Verification ==="

# 1. Import Test
echo "1. Testing imports..."
python3 -c "
from utils.mimo_engine import get_engine
from utils.ai_memory import get_memory
from utils.ai_tools import get_tools, execute_tool
from utils.ai_prompts import get_system_prompt
from utils.ai_planner import get_planner
from utils.scheduler import get_scheduler
print('✅ All imports successful')
"

# 2. Database Test
echo "2. Testing database..."
python3 -c "
from models.database import Database
db = Database()
# Test basic queries
print('✅ Database connection OK')
"

# 3. Engine Health Test
echo "3. Testing engine health..."
python3 -c "
from utils.mimo_engine import get_engine
engine = get_engine()
health = engine.health_check()
print(f'Engine status: {health[\"status\"]}')
"

# 4. Memory Test
echo "4. Testing memory..."
python3 -c "
from utils.ai_memory import get_memory
memory = get_memory()
# Test store and retrieve
memory.store_event('test', {'msg': 'verification'}, 'test', 'success', 1.0)
events = memory.get_recent_events(limit=1)
print(f'Memory test: {\"OK\" if events else \"FAILED\"}')
"

# 5. Tools Test
echo "5. Testing tools..."
python3 -c "
from utils.ai_tools import get_tools
tools = get_tools()
tool_list = tools.get_tool_list()
print(f'Tools loaded: {len(tool_list)}')
"

# 6. Flask App Test
echo "6. Testing Flask app..."
python3 -c "
from web.app import app
with app.test_client() as client:
    response = client.get('/ai/health')
    print(f'Health endpoint: {response.status_code}')
"

echo "=== Verification Complete ==="
```

### Quick Health Check Command
```bash
# Run this anytime to check system status
cd /Users/agastya/coding/agents/brewery_manager && python3 -c "
import sys
sys.path.insert(0, '.')

print('🏥 AI System Health Check')
print('=' * 30)

checks = []

# Check imports
try:
    from utils.mimo_engine import get_engine
    checks.append(('MIMO Engine', '✅'))
except: checks.append(('MIMO Engine', '❌'))

try:
    from utils.ai_memory import get_memory
    checks.append(('AI Memory', '✅'))
except: checks.append(('AI Memory', '❌'))

try:
    from utils.ai_tools import get_tools
    checks.append(('AI Tools', '✅'))
except: checks.append(('AI Tools', '❌'))

try:
    from utils.ai_planner import get_planner
    checks.append(('AI Planner', '✅'))
except: checks.append(('AI Planner', '❌'))

try:
    from utils.scheduler import get_scheduler
    checks.append(('Scheduler', '✅'))
except: checks.append(('Scheduler', '❌'))

try:
    from web.app import app
    checks.append(('Flask App', '✅'))
except: checks.append(('Flask App', '❌'))

for name, status in checks:
    print(f'{status} {name}')

print('=' * 30)
all_ok = all(s == '✅' for _, s in checks)
print(f'Overall: {\"✅ ALL SYSTEMS GO\" if all_ok else \"⚠️  ISSUES DETECTED\"}')
"
```

---

## 📞 Troubleshooting Guide

### Issue: "ModuleNotFoundError: No module named 'utils'"
**Solution:**
```bash
cd /Users/agastya/coding/agents/brewery_manager
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
# Or add to .env
echo "PYTHONPATH=$(pwd)" >> .env
```

### Issue: "database is locked"
**Solution:**
```bash
# Check for lock files
ls -la data/brewery.db*
# Remove WAL/SHM files if present
rm -f data/brewery.db-shm data/brewery.db-wal
# Restart application
```

### Issue: "aiohttp connection refused"
**Solution:**
```bash
# Check MIMO_API_KEY and MIMO_API_URL in .env
cat .env | grep MIMO
# Test API connectivity
curl -v https://api.mimo.ai/v1/health
```

### Issue: "Flask app won't start"
**Solution:**
```bash
# Check port availability
lsof -i :5000
# Kill existing process
kill -9 $(lsof -t -i:5000) 2>/dev/null
# Start with debug
python3 run.py --debug
```

### Issue: "Tests failing"
**Solution:**
```bash
cd /Users/agastya/coding/agents/brewery_manager
# Run specific test with verbose output
python3 -m pytest tests/test_ai_memory.py -v
# Run all tests
python3 -m pytest tests/ -v --tb=short
```

---

## 📝 Implementation Log

Use this section to track your progress:

| Date | Phase | Status | Notes |
|------|-------|--------|-------|
| | Pre-Implementation | | |
| | Phase 1: Core Engine | | |
| | Phase 2: Tools & Integration | | |
| | Phase 3: Planning System | | |
| | Verification | | |

---

## 🎯 Next Steps After Implementation

1. **Run full test suite:** `python3 -m pytest tests/ -v`
2. **Start the application:** `python3 run.py`
3. **Access AI dashboard:** http://localhost:5000/ai/dashboard
4. **Test AI chat:** http://localhost:5000/ai/manager
5. **Monitor logs:** `tail -f logs/app.log`

---

*Last Updated: 2026-04-17*
*Version: 2.0*