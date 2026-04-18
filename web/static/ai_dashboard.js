/**
 * AI Dashboard - Real-time monitoring, charts, and agent visualization
 */

// WebSocket connection for real-time updates
let wsConnection = null;
let wsReconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

// Chart instances
let activityChart = null;
let roiChart = null;
let performanceChart = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function () {
    initWebSocket();
    initCharts();
    initRealTimeUpdates();
    loadAgentThinking();
    loadScheduledImprovements();
    loadROIMetrics();
    loadAlerts();
});

/**
 * WebSocket Connection Management
 */
function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/ai-updates`;

    try {
        wsConnection = new WebSocket(wsUrl);

        wsConnection.onopen = function () {
            console.log('WebSocket connected');
            wsReconnectAttempts = 0;
            updateConnectionStatus('connected');

            // Subscribe to AI updates
            wsConnection.send(JSON.stringify({
                type: 'subscribe',
                channels: ['ai_activity', 'agent_thinking', 'alerts', 'improvements']
            }));
        };

        wsConnection.onmessage = function (event) {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        };

        wsConnection.onclose = function () {
            console.log('WebSocket disconnected');
            updateConnectionStatus('disconnected');

            // Attempt reconnection
            if (wsReconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                wsReconnectAttempts++;
                setTimeout(initWebSocket, 3000 * wsReconnectAttempts);
            }
        };

        wsConnection.onerror = function (error) {
            console.error('WebSocket error:', error);
            updateConnectionStatus('error');
        };
    } catch (e) {
        console.log('WebSocket not available, falling back to polling');
        initPollingFallback();
    }
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'ai_activity':
            handleNewActivity(data.payload);
            break;
        case 'agent_thinking':
            updateAgentThinking(data.payload);
            break;
        case 'alert':
            handleNewAlert(data.payload);
            break;
        case 'improvement_update':
            updateImprovementStatus(data.payload);
            break;
        case 'metrics_update':
            updateDashboardMetrics(data.payload);
            break;
        case 'schedule_update':
            updateScheduleVisualization(data.payload);
            break;
        default:
            console.log('Unknown message type:', data.type);
    }
}

function updateConnectionStatus(status) {
    const indicator = document.getElementById('ws-status-indicator');
    const statusText = document.getElementById('ws-status-text');

    if (indicator && statusText) {
        indicator.className = `status-dot status-${status}`;
        statusText.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    }
}

function initPollingFallback() {
    // Fallback to polling if WebSocket is not available
    setInterval(() => {
        fetchLatestActivity();
        fetchAgentStatus();
    }, 5000);
}

/**
 * Real-time Activity Feed
 */
function handleNewActivity(activity) {
    const feed = document.getElementById('activityFeed');
    if (!feed) return;

    const activityHtml = createActivityItem(activity);
    feed.insertAdjacentHTML('afterbegin', activityHtml);

    // Animate new item
    const newItem = feed.firstElementChild;
    newItem.classList.add('activity-new');
    setTimeout(() => newItem.classList.remove('activity-new'), 1000);

    // Update count
    updateActivityCount();

    // Remove old items if too many
    const items = feed.querySelectorAll('.activity-item');
    if (items.length > 50) {
        items[items.length - 1].remove();
    }
}

function createActivityItem(activity) {
    const typeColors = {
        'analysis': 'info',
        'suggestion': 'warning',
        'action': 'success',
        'alert': 'danger',
        'improvement': 'primary',
        'scheduled': 'secondary'
    };

    const typeIcons = {
        'analysis': 'fas fa-search',
        'suggestion': 'fas fa-lightbulb',
        'action': 'fas fa-bolt',
        'alert': 'fas fa-exclamation-triangle',
        'improvement': 'fas fa-rocket',
        'scheduled': 'fas fa-calendar-check'
    };

    const color = typeColors[activity.activity_type] || 'secondary';
    const icon = typeIcons[activity.activity_type] || 'fas fa-circle';

    return `
        <div class="border-bottom p-3 activity-item" data-activity-id="${activity.id}">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <span class="badge badge-${color}">
                        <i class="${icon}"></i> ${activity.activity_type.toUpperCase()}
                    </span>
                    <span class="ml-2">${escapeHtml(activity.description)}</span>
                </div>
                <small class="text-muted">${formatTimestamp(activity.timestamp)}</small>
            </div>
            ${activity.result ? `
                <small class="text-success mt-1 d-block">
                    <i class="fas fa-check-circle"></i> ${escapeHtml(activity.result)}
                </small>
            ` : ''}
            ${activity.impact ? `
                <div class="mt-2">
                    <span class="badge badge-light">
                        <i class="fas fa-chart-line"></i> Impact: ${activity.impact}
                    </span>
                </div>
            ` : ''}
        </div>
    `;
}

function updateActivityCount() {
    const countEl = document.getElementById('activityCount');
    const feed = document.getElementById('activityFeed');
    if (countEl && feed) {
        countEl.textContent = feed.querySelectorAll('.activity-item').length;
    }
}

/**
 * Agent Thinking Process Visualization
 */
function loadAgentThinking() {
    fetch('/api/ai/thinking-process')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                renderAgentThinking(data.thinking_steps || []);
            }
        })
        .catch(err => console.error('Failed to load thinking process:', err));
}

function updateAgentThinking(thinking) {
    const container = document.getElementById('agentThinkingContainer');
    if (!container) return;

    const thinkingHtml = `
        <div class="thinking-step thinking-active" data-step-id="${thinking.id}">
            <div class="thinking-header">
                <span class="thinking-icon">🧠</span>
                <span class="thinking-phase">${escapeHtml(thinking.phase)}</span>
                <span class="thinking-time">${formatTimestamp(thinking.timestamp)}</span>
            </div>
            <div class="thinking-content">
                <div class="thinking-prompt">
                    <strong>Context:</strong> ${escapeHtml(thinking.context)}
                </div>
                <div class="thinking-analysis">
                    <strong>Analysis:</strong>
                    <pre>${escapeHtml(thinking.analysis)}</pre>
                </div>
                ${thinking.confidence ? `
                    <div class="thinking-confidence">
                        <span>Confidence:</span>
                        <div class="progress" style="height: 8px;">
                            <div class="progress-bar bg-success" style="width: ${thinking.confidence}%"></div>
                        </div>
                        <span>${thinking.confidence}%</span>
                    </div>
                ` : ''}
            </div>
            <div class="thinking-actions" style="display: none;">
                <button class="btn btn-sm btn-outline-primary" onclick="approveThinking('${thinking.id}')">
                    <i class="fas fa-check"></i> Approve
                </button>
                <button class="btn btn-sm btn-outline-secondary" onclick="viewDetails('${thinking.id}')">
                    <i class="fas fa-eye"></i> Details
                </button>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('afterbegin', thinkingHtml);

    // Animate new thinking step
    const newStep = container.firstElementChild;
    newStep.classList.add('thinking-new');
    setTimeout(() => newStep.classList.remove('thinking-new'), 500);
}

function renderAgentThinking(steps) {
    const container = document.getElementById('agentThinkingContainer');
    if (!container) return;

    container.innerHTML = steps.map(step => `
        <div class="thinking-step ${step.status === 'active' ? 'thinking-active' : ''}" data-step-id="${step.id}">
            <div class="thinking-header">
                <span class="thinking-icon">${getPhaseIcon(step.phase)}</span>
                <span class="thinking-phase">${escapeHtml(step.phase)}</span>
                <span class="thinking-time">${formatTimestamp(step.timestamp)}</span>
            </div>
            <div class="thinking-content">
                <div class="thinking-prompt">
                    <strong>Context:</strong> ${escapeHtml(step.context)}
                </div>
                <div class="thinking-analysis">
                    <strong>Analysis:</strong>
                    <pre>${escapeHtml(step.analysis)}</pre>
                </div>
                ${step.confidence ? `
                    <div class="thinking-confidence">
                        <div class="progress" style="height: 6px; flex: 1;">
                            <div class="progress-bar bg-${getConfidenceColor(step.confidence)}" style="width: ${step.confidence}%"></div>
                        </div>
                        <span class="ml-2">${step.confidence}%</span>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
}

function getPhaseIcon(phase) {
    const icons = {
        'observation': '👁️',
        'analysis': '🔍',
        'planning': '📋',
        'decision': '🎯',
        'execution': '⚡',
        'verification': '✅'
    };
    return icons[phase] || '💭';
}

function getConfidenceColor(confidence) {
    if (confidence >= 80) return 'success';
    if (confidence >= 60) return 'info';
    if (confidence >= 40) return 'warning';
    return 'danger';
}

/**
 * Charts Initialization
 */
function initCharts() {
    initActivityChart();
    initROIChart();
    initPerformanceChart();
}

function initActivityChart() {
    const ctx = document.getElementById('activityChart');
    if (!ctx) return;

    activityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'AI Activities',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });

    // Load initial data
    fetchActivityChartData();
}

function initROIChart() {
    const ctx = document.getElementById('roiChart');
    if (!ctx) return;

    roiChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Time Saved', 'Cost Reduction', 'Revenue Impact', 'Efficiency Gain'],
            datasets: [{
                data: [0, 0, 0, 0],
                backgroundColor: [
                    'rgba(54, 162, 235, 0.8)',
                    'rgba(75, 192, 192, 0.8)',
                    'rgba(255, 206, 86, 0.8)',
                    'rgba(153, 102, 255, 0.8)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });
}

function initPerformanceChart() {
    const ctx = document.getElementById('performanceChart');
    if (!ctx) return;

    performanceChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Suggestions', 'Implemented', 'Success Rate', 'ROI'],
            datasets: [{
                label: 'Performance Metrics',
                data: [0, 0, 0, 0],
                backgroundColor: [
                    'rgba(255, 99, 132, 0.8)',
                    'rgba(54, 162, 235, 0.8)',
                    'rgba(75, 192, 192, 0.8)',
                    'rgba(255, 206, 86, 0.8)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

function fetchActivityChartData() {
    fetch('/api/ai/activity-stats?period=7d')
        .then(res => res.json())
        .then(data => {
            if (data.success && activityChart) {
                activityChart.data.labels = data.labels;
                activityChart.data.datasets[0].data = data.values;
                activityChart.update();
            }
        })
        .catch(err => console.error('Failed to load activity chart data:', err));
}

/**
 * ROI Tracking
 */
function loadROIMetrics() {
    fetch('/api/ai/roi-metrics')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                renderROIMetrics(data.metrics);
                updateROIChart(data.breakdown);
            }
        })
        .catch(err => console.error('Failed to load ROI metrics:', err));
}

function renderROIMetrics(metrics) {
    const container = document.getElementById('roiMetricsContainer');
    if (!container) return;

    container.innerHTML = `
        <div class="row">
            <div class="col-md-3">
                <div class="roi-card bg-primary text-white">
                    <div class="roi-icon">⏱️</div>
                    <div class="roi-value">${metrics.time_saved_hours || 0}h</div>
                    <div class="roi-label">Time Saved</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="roi-card bg-success text-white">
                    <div class="roi-icon">💰</div>
                    <div class="roi-value">$${formatNumber(metrics.cost_saved || 0)}</div>
                    <div class="roi-label">Cost Saved</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="roi-card bg-info text-white">
                    <div class="roi-icon">📈</div>
                    <div class="roi-value">${metrics.improvements_count || 0}</div>
                    <div class="roi-label">Improvements</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="roi-card bg-warning text-dark">
                    <div class="roi-icon">🎯</div>
                    <div class="roi-value">${metrics.success_rate || 0}%</div>
                    <div class="roi-label">Success Rate</div>
                </div>
            </div>
        </div>
    `;
}

function updateROIChart(breakdown) {
    if (roiChart && breakdown) {
        roiChart.data.datasets[0].data = [
            breakdown.time_savings || 0,
            breakdown.cost_reduction || 0,
            breakdown.revenue_impact || 0,
            breakdown.efficiency_gain || 0
        ];
        roiChart.update();
    }
}

/**
 * Scheduled Improvements Visualization
 */
function loadScheduledImprovements() {
    fetch('/api/ai/scheduled-improvements')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                renderScheduleTimeline(data.schedule || []);
            }
        })
        .catch(err => console.error('Failed to load schedule:', err));
}

function renderScheduleTimeline(schedule) {
    const container = document.getElementById('scheduleTimeline');
    if (!container) return;

    if (schedule.length === 0) {
        container.innerHTML = '<p class="text-muted text-center">No scheduled improvements</p>';
        return;
    }

    container.innerHTML = schedule.map(item => `
        <div class="timeline-item ${item.status}" data-schedule-id="${item.id}">
            <div class="timeline-marker">
                ${getStatusIcon(item.status)}
            </div>
            <div class="timeline-content">
                <div class="timeline-header">
                    <strong>${escapeHtml(item.title)}</strong>
                    <span class="badge badge-${getStatusColor(item.status)}">${item.status}</span>
                </div>
                <div class="timeline-body">
                    <p>${escapeHtml(item.description)}</p>
                    <div class="timeline-meta">
                        <span><i class="fas fa-calendar"></i> ${formatDate(item.scheduled_date)}</span>
                        <span><i class="fas fa-clock"></i> ${item.estimated_duration || 'N/A'}</span>
                        <span><i class="fas fa-tag"></i> ${item.category}</span>
                    </div>
                </div>
                <div class="timeline-actions">
                    <button class="btn btn-sm btn-outline-primary" onclick="viewScheduledDetails('${item.id}')">
                        <i class="fas fa-eye"></i>
                    </button>
                    ${item.status === 'pending' ? `
                        <button class="btn btn-sm btn-outline-success" onclick="executeScheduled('${item.id}')">
                            <i class="fas fa-play"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="cancelScheduled('${item.id}')">
                            <i class="fas fa-times"></i>
                        </button>
                    ` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

function updateScheduleVisualization(update) {
    const item = document.querySelector(`[data-schedule-id="${update.id}"]`);
    if (item) {
        item.className = `timeline-item ${update.status}`;
        const badge = item.querySelector('.badge');
        if (badge) {
            badge.className = `badge badge-${getStatusColor(update.status)}`;
            badge.textContent = update.status;
        }
    }
}

function getStatusIcon(status) {
    const icons = {
        'pending': '⏳',
        'scheduled': '📅',
        'in_progress': '🔄',
        'completed': '✅',
        'failed': '❌',
        'cancelled': '🚫'
    };
    return icons[status] || '📋';
}

function getStatusColor(status) {
    const colors = {
        'pending': 'secondary',
        'scheduled': 'info',
        'in_progress': 'warning',
        'completed': 'success',
        'failed': 'danger',
        'cancelled': 'dark'
    };
    return colors[status] || 'secondary';
}

/**
 * Alerts System
 */
function loadAlerts() {
    fetch('/api/ai/alerts')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                renderAlerts(data.alerts || []);
            }
        })
        .catch(err => console.error('Failed to load alerts:', err));
}

function handleNewAlert(alert) {
    const container = document.getElementById('alertsContainer');
    if (!container) return;

    const alertHtml = createAlertItem(alert);
    container.insertAdjacentHTML('afterbegin', alertHtml);

    // Show notification if supported
    if (Notification.permission === 'granted') {
        new Notification('AI Alert', {
            body: alert.message,
            icon: '/static/company-logo.svg'
        });
    }

    // Update alert count
    updateAlertCount();
}

function createAlertItem(alert) {
    const severityColors = {
        'critical': 'danger',
        'high': 'warning',
        'medium': 'info',
        'low': 'secondary'
    };

    const color = severityColors[alert.severity] || 'info';

    return `
        <div class="alert alert-${color} alert-dismissible fade show" role="alert" data-alert-id="${alert.id}">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <strong><i class="fas fa-exclamation-triangle"></i> ${alert.severity.toUpperCase()}</strong>
                    <p class="mb-1">${escapeHtml(alert.message)}</p>
                    <small class="text-muted">${formatTimestamp(alert.timestamp)}</small>
                </div>
                <button type="button" class="close" onclick="dismissAlert('${alert.id}')">
                    <span>&times;</span>
                </button>
            </div>
            ${alert.action_required ? `
                <div class="mt-2">
                    <button class="btn btn-sm btn-outline-${color}" onclick="handleAlertAction('${alert.id}')">
                        <i class="fas fa-bolt"></i> Take Action
                    </button>
                </div>
            ` : ''}
        </div>
    `;
}

function renderAlerts(alerts) {
    const container = document.getElementById('alertsContainer');
    if (!container) return;

    container.innerHTML = alerts.map(alert => createAlertItem(alert)).join('');
    updateAlertCount();
}

function dismissAlert(alertId) {
    fetch(`/api/ai/alerts/${alertId}/dismiss`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const alert = document.querySelector(`[data-alert-id="${alertId}"]`);
                if (alert) alert.remove();
                updateAlertCount();
            }
        });
}

function updateAlertCount() {
    const container = document.getElementById('alertsContainer');
    const badge = document.getElementById('alertCountBadge');
    if (container && badge) {
        const count = container.querySelectorAll('.alert').length;
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline' : 'none';
    }
}

/**
 * Utility Functions
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTimestamp(timestamp) {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
}

function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString();
}

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

/**
 * Refresh Functions
 */
function loadMoreActivity() {
    const feed = document.getElementById('activityFeed');
    const currentCount = feed ? feed.querySelectorAll('.activity-item').length : 0;

    fetch(`/api/ai/activity-log?offset=${currentCount}&limit=20`)
        .then(res => res.json())
        .then(data => {
            if (data.success && data.activities) {
                data.activities.forEach(activity => {
                    feed.insertAdjacentHTML('beforeend', createActivityItem(activity));
                });
            }
        });
}

function refreshDashboard() {
    loadROIMetrics();
    loadScheduledImprovements();
    loadAlerts();
    loadAgentThinking();
    fetchActivityChartData();
}

// Auto-refresh every 30 seconds
setInterval(refreshDashboard, 30000);

// Request notification permission
if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
}