/**
 * AI Chat Interface - Handles communication with MiMo AI
 */

let isLoading = false;

// Quick action messages
const quickActions = {
    dashboard: "Show me a complete dashboard summary of brewery operations",
    inventory: "Check current inventory levels and alert me about low stock items",
    production: "What is the current production status? Show all active batches",
    staff: "Who is available to work today? Show staff status",
    tasks: "What tasks do we have for today?",
    sales: "Show me today's sales and revenue report"
};

function sendQuickAction(action) {
    const message = quickActions[action];
    if (message) {
        document.getElementById('chat-input').value = message;
        sendMessage();
    }
}

function useCommand(element) {
    const text = element.textContent.trim().replace(/^"|"$/g, '');
    document.getElementById('chat-input').value = text;
    sendMessage();
}

function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();

    if (!message || isLoading) return;

    isLoading = true;
    input.value = '';

    // Add user message to chat
    addMessage('user', message);

    // Show loading indicator
    showToolIndicator(true);

    try {
        const response = await fetch('/ai/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        });

        const data = await response.json();

        if (data.error) {
            addMessage('error', data.error);
        } else {
            // Show tool usage if any
            if (data.tool_results && data.tool_results.length > 0) {
                for (const tool of data.tool_results) {
                    addToolMessage(tool.tool, tool.result);
                }
            }
            // Show AI response
            addMessage('assistant', data.response || data.content);

            // Handle proactive suggestions
            if (data.proactive_suggestions && data.proactive_suggestions.length > 0) {
                displayProactiveSuggestions(data.proactive_suggestions);
            }
        }
    } catch (error) {
        addMessage('error', 'Connection error. Please try again.');
    } finally {
        showToolIndicator(false);
        isLoading = false;
    }
}

// Autonomy level functions
let currentAutonomyLevel = 'observer';

function setAutonomy(level) {
    currentAutonomyLevel = level;

    // Update button styles
    document.querySelectorAll('.autonomy-btn').forEach(btn => {
        if (btn.dataset.level === level) {
            btn.style.background = '#2d2d2d';
            btn.style.borderColor = '#2d2d2d';
            btn.style.color = 'white';
            btn.classList.add('active');
        } else {
            btn.style.background = '#f5f5f5';
            btn.style.borderColor = '#dddddd';
            btn.style.color = '#333333';
            btn.classList.remove('active');
        }
    });

    // Update label
    const labels = {
        'off': '⛔ Off',
        'observer': '👁️ Observer',
        'suggester': '💡 Suggester',
        'actor': '🎬 Actor',
        'autonomous': '🤖 Autonomous'
    };
    document.getElementById('autonomy-level-label').textContent = labels[level] || level;

    // Send mode change to server
    fetch('/api/ai/autonomy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ level })
    }).then(response => response.json())
        .then(data => {
            if (data.success) {
                addMessage('assistant', '🎯 Autonomy level set to **' + (labels[level] || level) + '**');
                loadActivityLog();
            }
        });
}

async function runProactiveScan() {
    const scanBtn = document.getElementById('scan-btn');
    scanBtn.disabled = true;
    scanBtn.textContent = '🔄 Scanning...';
    scanBtn.style.background = '#9ca3af';

    try {
        const response = await fetch('/api/ai/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();

        if (data.success) {
            if (data.suggestions && data.suggestions.length > 0) {
                addMessage('assistant', '🔍 Scan complete! Found **' + data.count + '** suggestions.');
                loadPendingSuggestions();
            } else {
                addMessage('assistant', '✅ Scan complete! No issues found. Brewery operations look good.');
            }
        } else {
            addMessage('error', 'Scan failed: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        addMessage('error', 'Scan failed: ' + error.message);
    } finally {
        scanBtn.disabled = false;
        scanBtn.textContent = '🔍 Scan for Opportunities';
        scanBtn.style.background = '#1a73e8';
    }
}

async function loadPendingSuggestions() {
    try {
        const response = await fetch('/api/ai/suggestions/pending');
        const data = await response.json();

        if (data.success) {
            renderPendingSuggestions(data.suggestions || []);
        }
    } catch (error) {
        console.log('Failed to load pending suggestions:', error);
    }
}

function renderPendingSuggestions(suggestions) {
    const list = document.getElementById('pending-suggestions-list');
    const countBadge = document.getElementById('pending-count');

    if (!suggestions || suggestions.length === 0) {
        list.innerHTML = '<div style="font-size: 0.8em; color: #999999; font-style: italic;">No pending suggestions</div>';
        countBadge.style.display = 'none';
        return;
    }

    countBadge.textContent = suggestions.length;
    countBadge.style.display = 'inline';

    list.innerHTML = '';
    suggestions.forEach((s, i) => {
        const div = document.createElement('div');
        const priorityColor = s.priority === 'high' ? '#ef4444' : s.priority === 'medium' ? '#f59e0b' : '#6b7280';
        const typeIcon = getSuggestionIcon(s.type);
        div.style.cssText = 'background: #f8f9fa; border: 1px solid #e5e7eb; border-radius: 6px; padding: 8px 10px; font-size: 0.75em; color: #333333;';
        div.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 4px;">
                <span style="font-weight: 600;">${typeIcon} ${s.type}</span>
                <span style="color: ${priorityColor}; font-size: 0.9em;">${s.priority}</span>
            </div>
            <div style="margin-bottom: 6px; color: #666666;">${s.message.substring(0, 80)}${s.message.length > 80 ? '...' : ''}</div>
            <div style="display: flex; gap: 4px;">
                <button onclick="approveSuggestion(${i})" style="flex: 1; background: #10b981; color: white; border: none; border-radius: 4px; padding: 3px 6px; cursor: pointer; font-size: 0.95em;">✓</button>
                <button onclick="dismissSuggestion(${i})" style="flex: 1; background: #ef4444; color: white; border: none; border-radius: 4px; padding: 3px 6px; cursor: pointer; font-size: 0.95em;">✗</button>
            </div>
        `;
        list.appendChild(div);
    });
}

async function approveSuggestion(index) {
    try {
        const response = await fetch(`/api/ai/suggestions/${index}/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (data.success) {
            addMessage('assistant', '✅ Suggestion approved and action taken.');
            loadPendingSuggestions();
            loadActivityLog();
        }
    } catch (error) {
        addMessage('error', 'Failed to approve suggestion');
    }
}

async function dismissSuggestion(index) {
    try {
        const response = await fetch(`/api/ai/suggestions/${index}/dismiss`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (data.success) {
            loadPendingSuggestions();
        }
    } catch (error) {
        addMessage('error', 'Failed to dismiss suggestion');
    }
}

async function loadActivityLog() {
    try {
        const response = await fetch('/api/ai/activity-log?limit=15');
        const data = await response.json();

        if (data.success) {
            renderActivityLog(data.activities || []);
        }
    } catch (error) {
        console.log('Failed to load activity log:', error);
    }
}

function renderActivityLog(activities) {
    const logDiv = document.getElementById('activity-log');

    if (!activities || activities.length === 0) {
        logDiv.innerHTML = '<div style="font-style: italic;">No recent activity</div>';
        return;
    }

    logDiv.innerHTML = '';
    activities.forEach(a => {
        const div = document.createElement('div');
        const typeIcon = getSuggestionIcon(a.type);
        const actionColor = a.action === 'executed' ? '#10b981' : a.action === 'approved' ? '#3b82f6' : '#6b7280';
        const time = new Date(a.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        div.style.cssText = 'padding: 4px 0; border-bottom: 1px solid #f0f0f0;';
        div.innerHTML = `
            <span style="color: ${actionColor};">●</span>
            ${typeIcon} ${a.message.substring(0, 50)}${a.message.length > 50 ? '...' : ''}
            <span style="float: right; color: #aaaaaa;">${time}</span>
        `;
        logDiv.appendChild(div);
    });
}

function displayProactiveSuggestions(suggestions) {
    renderPendingSuggestions(suggestions);
}

function getSuggestionIcon(type) {
    const icons = {
        'production': '🏭',
        'inventory': '📦',
        'financial': '💰',
        'staff': '👥',
        'quality': '✅',
        'equipment': '🔧',
        'customer': '👤',
        'system': '⚙️',
        'general': '💡'
    };
    return icons[type] || '💡';
}

function addMessage(role, content) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    let avatar = '🤖';
    if (role === 'user') avatar = '👤';
    else if (role === 'error') avatar = '⚠️';

    let ttsButton = '';
    if (role === 'assistant') {
        ttsButton = `<button class="tts-button" onclick="playTTS(this, '${encodeURIComponent(content)}')" title="Play Audio" style="background:none; border:none; cursor:pointer; font-size:1.1em; opacity:0.7;">🔊</button>`;
    }

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <p>${formatMessage(content)}</p>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px;">
                <span class="message-time">${new Date().toLocaleTimeString()}</span>
                ${ttsButton}
            </div>
        </div>
    `;

    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

async function playTTS(btn, textUriEncoded) {
    const originalText = decodeURIComponent(textUriEncoded);
    if (btn.classList.contains('playing')) {
        if (window.currentAudio) {
            window.currentAudio.pause();
            window.currentAudio = null;
        }
        btn.classList.remove('playing');
        btn.innerHTML = '🔊';
        return;
    }

    btn.innerHTML = '⏳';
    btn.disabled = true;

    try {
        const response = await fetch('/api/ai/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: originalText })
        });
        
        if (!response.ok) throw new Error('TTS Failed');
        
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        
        if (window.currentAudio) window.currentAudio.pause();
        
        window.currentAudio = new Audio(url);
        window.currentAudio.onended = () => {
            btn.innerHTML = '🔊';
            btn.classList.remove('playing');
            window.currentAudio = null;
        };
        
        window.currentAudio.play();
        btn.innerHTML = '⏹️';
        btn.classList.add('playing');
    } catch (e) {
        console.error("TTS error:", e);
        btn.innerHTML = '❌';
        setTimeout(() => btn.innerHTML = '🔊', 2000);
    } finally {
        btn.disabled = false;
    }
}

function addToolMessage(toolName, result) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message tool';

    const toolDisplayName = getToolDisplayName(toolName);
    const resultPreview = formatToolResult(result);

    messageDiv.innerHTML = `
        <div class="message-avatar">⚙️</div>
        <div class="message-content">
            <p class="tool-name">${toolDisplayName}</p>
            <div class="tool-result">${resultPreview}</div>
            <span class="message-time">${new Date().toLocaleTimeString()}</span>
        </div>
    `;

    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function formatMessage(text) {
    if (!text) return '';

    // Remove raw JSON blocks (common AI hallucination showing tool output)
    text = text.replace(/\{[\s]*"count"[\s]*:[\s]*\d+[\s]*,[\s]*"items"[\s]*:[\s]*\[.*?\][\s]*\}/gs, '');
    text = text.replace(/\{[\s]*"count"[\s]*:[\s]*\d+[\s]*,[\s]*"batches"[\s]*:[\s]*\[.*?\][\s]*\}/gs, '');
    text = text.replace(/\{[\s]*"count"[\s]*:[\s]*\d+[\s]*,[\s]*"staff"[\s]*:[\s]*\[.*?\][\s]*\}/gs, '');
    text = text.replace(/\{[\s]*"count"[\s]*:[\s]*\d+[\s]*,[\s]*"tasks"[\s]*:[\s]*\[.*?\][\s]*\}/gs, '');
    text = text.replace(/\{[\s]*"count"[\s]*:[\s]*\d+[\s]*,[\s]*"products"[\s]*:[\s]*\[.*?\][\s]*\}/gs, '');
    text = text.replace(/\{[\s]*"count"[\s]*:[\s]*\d+[\s]*,[\s]*"equipment"[\s]*:[\s]*\[.*?\][\s]*\}/gs, '');
    text = text.replace(/\{[\s]*"count"[\s]*:[\s]*\d+[\s]*,[\s]*"tanks"[\s]*:[\s]*\[.*?\][\s]*\}/gs, '');
    text = text.replace(/\{[\s]*"count"[\s]*:[\s]*\d+[\s]*,[\s]*"results"[\s]*:[\s]*\[.*?\][\s]*\}/gs, '');

    // Remove function call blocks (<tool_call> XML tags)
    text = text.replace(/<tool_call>[\s\S]*?<\/tool_call>/g, '');
    text = text.replace(/<tool_call>[\s\S]*?<\/tool_use>/g, '');
    text = text.replace(/<function_calls>[\s\S]*?<\/invoke>/g, '');
    text = text.replace(/<parameter name="[^"]*">[^<]*<\/parameter>/g, '');
    text = text.replace(/<\/?function_calls>/g, '');
    text = text.replace(/<\/?invoke>/g, '');
    text = text.replace(/<\/?tool_use>/g, '');
    text = text.replace(/<\/?tool_call>/g, '');
    text = text.replace(/```json[\s\S]*?```/g, '');

    // Clean up extra whitespace and newlines
    text = text.replace(/\n{3,}/g, '\n\n').trim();

    // If nothing left after cleaning, return empty
    if (!text || text.length < 3) return '';

    // Intercept <thinking> blocks and convert them to details accordion
    text = text.replace(/<thinking>([\s\S]*?)<\/thinking>/gi, function(match, innerContent) {
        return `<details class="thought-process"><summary>🧠 Thought Process</summary><div class="thought-content">${innerContent.trim()}</div></details>`;
    });

    // Parse everything with marked.js
    if (typeof marked !== 'undefined') {
        return marked.parse(text);
    }
    
    // Fallback if marked.js fails to load
    return text.replace(/\n/g, '<br>');
}

function formatToolResult(result) {
    if (typeof result === 'string') {
        try {
            result = JSON.parse(result);
        } catch (e) {
            return result;
        }
    }

    // Format inventory items with table
    if (result.items && Array.isArray(result.items)) {
        if (result.items.length === 0) return 'No items found';
        let html = `<strong>📦 Inventory (${result.count} items)</strong><table class="chat-table"><tr><th>Name</th><th>Qty</th><th>Min</th><th>Unit</th><th>Status</th></tr>`;
        result.items.forEach(item => {
            const qty = parseFloat(item.quantity) || 0;
            const minQty = parseFloat(item.min_quantity) || 0;
            let status, statusColor;
            if (qty <= 0) {
                status = '❌ Out of Stock';
                statusColor = '#dc2626';
            } else if (qty <= minQty) {
                status = '⚠️ Low Stock';
                statusColor = '#f59e0b';
            } else {
                status = '✅ OK';
                statusColor = '#16a34a';
            }
            html += `<tr><td>${item.name || 'N/A'}</td><td style="font-weight:bold;">${qty}</td><td style="color:#666;">${minQty}</td><td>${item.unit || ''}</td><td style="color:${statusColor};">${status}</td></tr>`;
        });
        html += '</table>';
        return html;
    }

    // Format batches with table
    if (result.batches && Array.isArray(result.batches)) {
        if (result.batches.length === 0) return 'No batches found';
        let html = `<strong>🏭 Batches (${result.count})</strong><table class="chat-table"><tr><th>Batch</th><th>Product</th><th>Status</th><th>Tank</th></tr>`;
        result.batches.forEach(b => {
            html += `<tr><td>${b.batch_number || b.id}</td><td>${b.product_name || 'N/A'}</td><td>${b.status}</td><td>${b.tank_name || 'N/A'}</td></tr>`;
        });
        html += '</table>';
        return html;
    }

    // Format staff with table
    if (result.staff && Array.isArray(result.staff)) {
        if (result.staff.length === 0) return 'No staff found';
        let html = `<strong>👥 Staff (${result.count})</strong><table class="chat-table"><tr><th>Name</th><th>Position</th><th>Department</th><th>Phone</th></tr>`;
        result.staff.forEach(s => {
            html += `<tr><td>${s.name || 'N/A'}</td><td>${s.position || s.role || 'N/A'}</td><td>${s.department || 'N/A'}</td><td>${s.phone || 'N/A'}</td></tr>`;
        });
        html += '</table>';
        return html;
    }

    // Format tasks with table
    if (result.tasks && Array.isArray(result.tasks)) {
        if (result.tasks.length === 0) return 'No tasks for today';
        let html = `<strong>📋 Tasks (${result.count})</strong><table class="chat-table"><tr><th>Title</th><th>Assigned</th><th>Priority</th><th>Status</th></tr>`;
        result.tasks.forEach(t => {
            const priority = t.priority === 'urgent' ? '🔴' : t.priority === 'high' ? '🟡' : '🟢';
            html += `<tr><td>${t.title}</td><td>${t.assignee_name || 'Unassigned'}</td><td>${priority} ${t.priority}</td><td>${t.status}</td></tr>`;
        });
        html += '</table>';
        return html;
    }

    // Format products with table
    if (result.products && Array.isArray(result.products)) {
        if (result.products.length === 0) return 'No products found';
        let html = `<strong>🍺 Products (${result.count})</strong><table class="chat-table"><tr><th>Name</th><th>Type</th><th>ABV</th><th>Price</th></tr>`;
        result.products.forEach(p => {
            html += `<tr><td>${p.name}</td><td>${p.beer_type || ''}</td><td>${p.abv || ''}%</td><td>${p.price ? '$' + p.price : ''}</td></tr>`;
        });
        html += '</table>';
        return html;
    }

    // Format dashboard summary
    if (result.active_batches !== undefined) {
        return `<strong>📊 Dashboard Summary</strong><br>
        🏭 Active Batches: <strong>${result.active_batches}</strong><br>
        📦 Pending Orders: <strong>${result.pending_orders}</strong><br>
        ⚠️ Low Stock Items: <strong>${result.low_stock_items}</strong><br>
        📋 Pending Tasks: <strong>${result.pending_tasks}</strong><br>
        👥 Active Staff: <strong>${result.active_staff}</strong><br>
        🔧 Available Equipment: <strong>${result.available_equipment}</strong>`;
    }

    // Format equipment with table
    if (result.equipment && Array.isArray(result.equipment)) {
        if (result.equipment.length === 0) return 'No equipment found';
        let html = `<strong>🔧 Equipment (${result.count})</strong><table class="chat-table"><tr><th>Name</th><th>Type</th><th>Status</th><th>Capacity</th></tr>`;
        result.equipment.forEach(e => {
            html += `<tr><td>${e.name}</td><td>${e.equipment_type}</td><td>${e.status}</td><td>${e.capacity || ''}</td></tr>`;
        });
        html += '</table>';
        return html;
    }

    // Format tanks
    if (result.tanks && Array.isArray(result.tanks)) {
        if (result.tanks.length === 0) return 'No tanks found';
        let html = `<strong>🫗 Tanks (${result.count})</strong><table class="chat-table"><tr><th>Name</th><th>Status</th><th>Current Batch</th></tr>`;
        result.tanks.forEach(t => {
            html += `<tr><td>${t.name}</td><td>${t.status}</td><td>${t.batch_number || 'Empty'}</td></tr>`;
        });
        html += '</table>';
        return html;
    }

    // Format sales results
    if (result.results && Array.isArray(result.results)) {
        if (result.results.length === 0) return 'No results found';
        let html = `<strong>💰 Results (${result.count})</strong><table class="chat-table">`;
        result.results.forEach(r => {
            if (r.customer_name) {
                html += `<tr><td>${r.customer_name}</td><td>${r.total_amount || ''}</td><td>${r.status || ''}</td></tr>`;
            } else if (r.name) {
                html += `<tr><td>${r.name}</td><td>Sold: ${r.total_sold || ''}</td><td>Revenue: ${r.total_revenue || ''}</td></tr>`;
            }
        });
        html += '</table>';
        return html;
    }

    // Format cost analysis
    if (result.transactions && Array.isArray(result.transactions)) {
        if (result.transactions.length === 0) return 'No transactions for this period';
        let html = `<strong>💵 Cost Analysis (${result.period})</strong><table class="chat-table"><tr><th>Type</th><th>Category</th><th>Amount</th></tr>`;
        result.transactions.forEach(t => {
            html += `<tr><td>${t.type}</td><td>${t.category || ''}</td><td>$${t.total}</td></tr>`;
        });
        html += '</table>';
        return html;
    }

    // Format success messages
    if (result.success) {
        return `<strong>✅ ${result.message || 'Action completed successfully'}</strong>`;
    }

    // Format revenue
    if (result.revenue !== undefined) {
        return `<strong>💰 Revenue: $${result.revenue}</strong>`;
    }

    // Format customers
    if (result.customers && Array.isArray(result.customers)) {
        if (result.customers.length === 0) return 'No customers found';
        let html = `<strong>👥 Customers (${result.count})</strong><table class="chat-table"><tr><th>Name</th><th>Phone</th><th>Email</th><th>Address</th></tr>`;
        result.customers.forEach(c => {
            html += `<tr><td>${c.name}</td><td>${c.phone || 'N/A'}</td><td>${c.email || 'N/A'}</td><td>${(c.address || 'N/A').substring(0, 30)}${c.address && c.address.length > 30 ? '...' : ''}</td></tr>`;
        });
        html += '</table>';
        return html;
    }

    // Format quality checks
    if (result.checks && Array.isArray(result.checks)) {
        if (result.checks.length === 0) return 'No quality checks found';
        let html = `<strong>🔬 Quality Checks (${result.count})</strong><table class="chat-table"><tr><th>Type</th><th>Value</th><th>Result</th><th>Date</th></tr>`;
        result.checks.forEach(q => {
            const status = q.passed ? '✅ Passed' : '❌ Failed';
            html += `<tr><td>${q.check_type}</td><td>${q.value}</td><td>${status}</td><td>${q.check_date}</td></tr>`;
        });
        html += '</table>';
        return html;
    }

    // Format transactions
    if (result.transactions && Array.isArray(result.transactions)) {
        if (result.transactions.length === 0) return 'No transactions found';
        let html = `<strong>💵 Transactions (${result.count})</strong><table class="chat-table"><tr><th>Type</th><th>Category</th><th>Amount</th><th>Date</th></tr>`;
        result.transactions.forEach(t => {
            const typeIcon = t.type === 'income' ? '📈' : '📉';
            html += `<tr><td>${typeIcon} ${t.type}</td><td>${t.category || 'N/A'}</td><td style="color:${t.type === 'income' ? 'green' : 'red'};">$${t.amount}</td><td>${t.transaction_date}</td></tr>`;
        });
        html += '</table>';
        return html;
    }

    // Format recipes
    if (result.recipes && Array.isArray(result.recipes)) {
        if (result.recipes.length === 0) return 'No recipes found';
        let html = `<strong>🍺 Recipes (${result.count})</strong><table class="chat-table"><tr><th>Name</th><th>Style</th><th>ABV</th><th>IBU</th></tr>`;
        result.recipes.forEach(r => {
            html += `<tr><td>${r.name}</td><td>${r.beer_type || 'N/A'}</td><td>${r.abv || 'N/A'}%</td><td>${r.ibu || 'N/A'}</td></tr>`;
        });
        html += '</table>';
        return html;
    }

    // Format order created
    if (result.order_id) {
        return `<strong>✅ Order #${result.order_id} created</strong><br>Total: $${result.total_amount || 0}<br>${result.message || ''}`;
    }

    // Format success messages
    if (result.success && !result.items && !result.batches) {
        return `<strong>✅ ${result.message || 'Action completed successfully'}</strong>`;
    }

    // Default: formatted JSON
    return JSON.stringify(result, null, 2).substring(0, 500);
}

function getToolDisplayName(toolName) {
    const names = {
        'query_inventory': '📦 Querying Inventory',
        'query_batches': '🏭 Checking Batches',
        'query_staff': '👥 Checking Staff',
        'query_sales': '💰 Checking Sales',
        'query_equipment': '🔧 Checking Equipment',
        'create_task': '✅ Creating Task',
        'update_task_status': '📝 Updating Task',
        'get_daily_tasks': '📋 Fetching Tasks',
        'schedule_batch': '📅 Scheduling Batch',
        'get_batch_status': '📊 Getting Batch Status',
        'check_stock_levels': '📉 Analyzing Stock',
        'get_products': '🍺 Loading Products',
        'get_staff_list': '👤 Loading Staff',
        'analyze_costs': '💵 Analyzing Costs',
        'get_dashboard_summary': '📊 Loading Dashboard',
        'search_products': '🔍 Searching Products',
        'search_staff': '🔍 Searching Staff',
        'get_tank_availability': '🫗 Checking Tanks',
        'create_order': '🛒 Creating Order',
        'query_customers': '👥 Querying Customers',
        'log_quality_check': '🔬 Logging Quality Check',
        'query_quality_checks': '🔬 Checking Quality',
        'query_transactions': '💵 Querying Transactions',
        'query_recipes': '🍺 Querying Recipes',
        'update_order_status': '📝 Updating Order',
        'add_inventory_item': '📦 Adding Inventory',
        'update_inventory_quantity': '📦 Updating Inventory'
    };
    return names[toolName] || `⚙️ ${toolName}`;
}

function showToolIndicator(show) {
    const indicator = document.getElementById('tool-indicator');
    const sendBtn = document.getElementById('send-btn');

    if (show) {
        indicator.classList.remove('hidden');
        indicator.classList.add('visible');
        sendBtn.disabled = true;
    } else {
        indicator.classList.remove('visible');
        indicator.classList.add('hidden');
        sendBtn.disabled = false;
    }
}

function clearChat() {
    const messagesDiv = document.getElementById('chat-messages');
    messagesDiv.innerHTML = `
        <div class="message assistant">
            <div class="message-avatar">🤖</div>
            <div class="message-content">
                <p>Chat cleared. How can I help you today?</p>
            </div>
        </div>
    `;

    // Clear server-side history
    fetch('/ai/clear', { method: 'POST' });
}

// Auto-focus input on page load
document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('chat-input').focus();

    // Auto-fetch proactive suggestions if planning mode is proactive or autonomous
    if (currentPlanningMode === 'proactive' || currentPlanningMode === 'autonomous') {
        fetchAndDisplaySuggestions();
    }
});

function fetchAndDisplaySuggestions() {
    fetch('/api/ai/suggestions')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.suggestions && data.suggestions.length > 0) {
                displayProactiveSuggestions(data.suggestions);
            }
        })
        .catch(err => console.log('Failed to fetch suggestions:', err));
}

// Periodically refresh suggestions every 5 minutes if in proactive/autonomous mode
setInterval(function () {
    if (currentPlanningMode === 'proactive' || currentPlanningMode === 'autonomous') {
        fetchAndDisplaySuggestions();
    }
}, 300000); // 5 minutes
