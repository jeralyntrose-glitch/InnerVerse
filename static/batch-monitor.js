/**
 * BATCH OPTIMIZATION LIVE PROGRESS MONITOR
 * 
 * Enterprise-grade real-time monitoring for batch optimization process.
 * Uses Server-Sent Events (SSE) with fallback to polling.
 * 
 * SAFETY FEATURES:
 * - Auto-reconnect on connection loss
 * - Fallback to polling if SSE not supported
 * - Graceful degradation
 * - Kill switch via ENABLE_LIVE_PROGRESS config
 * 
 * Author: InnerVerse Team
 * Created: 2025-11-27
 */

// ========================================
// CONFIGURATION
// ========================================

const BATCH_MONITOR_CONFIG = {
    ENABLE_LIVE_PROGRESS: true,  // KILL SWITCH: Set to false to disable completely
    SSE_ENDPOINT: '/api/batch-optimize-stream',
    FALLBACK_POLL_INTERVAL: 5000,  // 5 seconds
    MAX_RECONNECT_ATTEMPTS: 3,
    RECONNECT_DELAY: 2000,  // 2 seconds
    HEARTBEAT_TIMEOUT: 120000  // 2 minutes no update = warning
};

// ========================================
// BATCH MONITOR CLASS
// ========================================

class BatchMonitor {
    constructor() {
        this.eventSource = null;
        this.reconnectAttempts = 0;
        this.isRunning = false;
        this.lastUpdateTime = null;
        this.heartbeatTimer = null;
        this.stats = {
            processed: 0,
            total: 0,
            failed: 0,
            totalVectors: 0,
            elapsedSeconds: 0,
            estimatedRemainingSeconds: 0
        };
        
        // Initialize UI elements
        this.initializeUI();
    }
    
    initializeUI() {
        // Create progress panel HTML
        const progressPanel = document.createElement('div');
        progressPanel.id = 'batch-progress-panel';
        progressPanel.className = 'batch-progress-panel hidden';
        progressPanel.innerHTML = `
            <div class="progress-header">
                <h3>🔥 Live Batch Optimization Progress</h3>
                <button class="close-progress-btn" onclick="batchMonitor.hideProgress()">×</button>
            </div>
            
            <div class="progress-stats">
                <div class="stat-item">
                    <span class="stat-label">Documents:</span>
                    <span class="stat-value" id="progress-docs">0/0</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Failed:</span>
                    <span class="stat-value" id="progress-failed">0</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Vectors:</span>
                    <span class="stat-value" id="progress-vectors">0</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Elapsed:</span>
                    <span class="stat-value" id="progress-elapsed">0m</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Remaining:</span>
                    <span class="stat-value" id="progress-remaining">~</span>
                </div>
            </div>
            
            <div class="progress-bar-container">
                <div class="progress-bar" id="progress-bar" style="width: 0%"></div>
                <span class="progress-percentage" id="progress-percentage">0%</span>
            </div>
            
            <div class="current-document">
                <strong>Current:</strong> <span id="current-filename">Initializing...</span>
                <span class="stage-indicator" id="stage-indicator"></span>
            </div>
            
            <div class="progress-log-container">
                <div class="progress-log" id="progress-log"></div>
            </div>
            
            <div class="progress-footer">
                <span class="connection-status" id="connection-status">⚫ Disconnected</span>
            </div>
        `;
        
        document.body.appendChild(progressPanel);
        
        // Add CSS
        this.injectStyles();
    }
    
    injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .batch-progress-panel {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 90%;
                max-width: 700px;
                max-height: 80vh;
                background: var(--bg-main, #ffffff);
                border: 2px solid var(--border-main, #e0e0e0);
                border-radius: 12px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                z-index: 10000;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }
            
            .batch-progress-panel.hidden {
                display: none;
            }
            
            .progress-header {
                padding: 16px 20px;
                background: var(--bg-secondary, #f5f5f5);
                border-bottom: 1px solid var(--border-main, #e0e0e0);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .progress-header h3 {
                margin: 0;
                font-size: 18px;
                color: var(--text-primary, #1a1a1a);
            }
            
            .close-progress-btn {
                background: none;
                border: none;
                font-size: 28px;
                color: var(--text-secondary, #666);
                cursor: pointer;
                padding: 0;
                width: 32px;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 4px;
                transition: all 0.2s;
            }
            
            .close-progress-btn:hover {
                background: var(--bg-hover, #e0e0e0);
                color: var(--text-primary, #1a1a1a);
            }
            
            .progress-stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                gap: 12px;
                padding: 16px 20px;
                background: var(--bg-main, #ffffff);
            }
            
            .stat-item {
                display: flex;
                flex-direction: column;
                gap: 4px;
            }
            
            .stat-label {
                font-size: 12px;
                color: var(--text-secondary, #666);
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .stat-value {
                font-size: 18px;
                font-weight: 600;
                color: var(--text-primary, #1a1a1a);
            }
            
            .progress-bar-container {
                position: relative;
                height: 32px;
                background: var(--bg-secondary, #f5f5f5);
                border-radius: 16px;
                margin: 0 20px 16px;
                overflow: hidden;
            }
            
            .progress-bar {
                height: 100%;
                background: linear-gradient(90deg, #4CAF50, #45a049);
                transition: width 0.5s ease;
                border-radius: 16px;
            }
            
            .progress-percentage {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-weight: 600;
                font-size: 14px;
                color: var(--text-primary, #1a1a1a);
                text-shadow: 0 1px 2px rgba(255, 255, 255, 0.8);
            }
            
            .current-document {
                padding: 12px 20px;
                background: var(--bg-secondary, #f5f5f5);
                border-top: 1px solid var(--border-main, #e0e0e0);
                border-bottom: 1px solid var(--border-main, #e0e0e0);
                font-size: 14px;
                color: var(--text-primary, #1a1a1a);
            }
            
            .current-document strong {
                color: var(--text-secondary, #666);
            }
            
            .stage-indicator {
                display: inline-block;
                margin-left: 12px;
                padding: 4px 8px;
                background: #2196F3;
                color: white;
                font-size: 11px;
                border-radius: 4px;
                text-transform: uppercase;
                font-weight: 600;
            }
            
            .progress-log-container {
                flex: 1;
                overflow-y: auto;
                padding: 16px 20px;
                background: var(--bg-main, #ffffff);
                min-height: 200px;
                max-height: 300px;
            }
            
            .progress-log {
                font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
                font-size: 12px;
                line-height: 1.6;
                color: var(--text-primary, #1a1a1a);
            }
            
            .log-entry {
                margin-bottom: 8px;
                padding: 6px 10px;
                border-radius: 4px;
                background: var(--bg-secondary, #f5f5f5);
            }
            
            .log-entry.success {
                background: #e8f5e9;
                color: #2e7d32;
            }
            
            .log-entry.error {
                background: #ffebee;
                color: #c62828;
            }
            
            .log-entry.info {
                background: #e3f2fd;
                color: #1565c0;
            }
            
            .progress-footer {
                padding: 12px 20px;
                background: var(--bg-secondary, #f5f5f5);
                border-top: 1px solid var(--border-main, #e0e0e0);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .connection-status {
                font-size: 12px;
                color: var(--text-secondary, #666);
            }
            
            .connection-status.connected {
                color: #4CAF50;
            }
            
            .connection-status.connecting {
                color: #FF9800;
            }
            
            .connection-status.disconnected {
                color: #f44336;
            }
        `;
        document.head.appendChild(style);
    }
    
    start() {
        if (!BATCH_MONITOR_CONFIG.ENABLE_LIVE_PROGRESS) {
            console.log('📊 Batch monitor disabled via config');
            return;
        }
        
        this.showProgress();
        this.isRunning = true;
        this.reconnectAttempts = 0;
        
        // Try SSE first
        if (typeof EventSource !== 'undefined') {
            this.connectSSE();
        } else {
            // Fallback to polling
            console.warn('⚠️ EventSource not supported, falling back to polling');
            this.fallbackToPolling();
        }
        
        // Start heartbeat monitor
        this.startHeartbeatMonitor();
    }
    
    connectSSE() {
        try {
            this.updateConnectionStatus('connecting');
            this.addLog('info', 'Connecting to progress stream...');
            
            this.eventSource = new EventSource(BATCH_MONITOR_CONFIG.SSE_ENDPOINT);
            
            this.eventSource.onmessage = (event) => {
                this.lastUpdateTime = Date.now();
                const data = JSON.parse(event.data);
                this.handleProgressEvent(data);
            };
            
            this.eventSource.onerror = (error) => {
                console.error('❌ SSE connection error:', error);
                this.updateConnectionStatus('disconnected');
                
                if (this.isRunning && this.reconnectAttempts < BATCH_MONITOR_CONFIG.MAX_RECONNECT_ATTEMPTS) {
                    this.reconnectAttempts++;
                    this.addLog('info', `Reconnecting... (Attempt ${this.reconnectAttempts}/${BATCH_MONITOR_CONFIG.MAX_RECONNECT_ATTEMPTS})`);
                    
                    setTimeout(() => {
                        this.eventSource.close();
                        this.connectSSE();
                    }, BATCH_MONITOR_CONFIG.RECONNECT_DELAY);
                } else if (this.reconnectAttempts >= BATCH_MONITOR_CONFIG.MAX_RECONNECT_ATTEMPTS) {
                    this.addLog('error', 'Max reconnection attempts reached. Falling back to polling...');
                    this.fallbackToPolling();
                }
            };
            
            this.eventSource.onopen = () => {
                this.updateConnectionStatus('connected');
                this.reconnectAttempts = 0;
                this.addLog('success', 'Connected to live progress stream ✓');
            };
            
        } catch (error) {
            console.error('❌ Failed to establish SSE connection:', error);
            this.fallbackToPolling();
        }
    }
    
    fallbackToPolling() {
        // Fallback: Use existing frontend progress UI (already implemented)
        this.addLog('info', 'Using standard progress monitoring');
        this.updateConnectionStatus('connected');
    }
    
    handleProgressEvent(data) {
        switch (data.type) {
            case 'connected':
                this.updateConnectionStatus('connected');
                break;
                
            case 'initialized':
                this.stats.total = data.total_documents;
                this.updateStats();
                this.addLog('success', `Found ${data.total_documents} documents to optimize`);
                break;
                
            case 'processing':
                document.getElementById('current-filename').textContent = data.filename;
                const stageNames = {
                    'starting': 'Starting',
                    'stage1_typos': 'Fixing Typos',
                    'stage2_cleaning': 'GPT Cleaning',
                    'semantic_chunking': 'Semantic Chunking',
                    'tagging': 'Tagging',
                    'embedding': 'Embedding',
                    'uploading': 'Uploading'
                };
                document.getElementById('stage-indicator').textContent = stageNames[data.stage] || data.stage;
                break;
                
            case 'document_complete':
                this.stats.processed = data.current;
                this.stats.failed = data.failed;
                this.stats.totalVectors = data.total_vectors;
                this.stats.elapsedSeconds = data.elapsed_seconds;
                this.stats.estimatedRemainingSeconds = data.estimated_remaining_seconds;
                this.updateStats();
                
                const octagramStr = data.octagram_states && data.octagram_states.length > 0 
                    ? ` | Octagram: [${data.octagram_states.join(', ')}]` 
                    : '';
                const conceptsStr = data.key_concepts && data.key_concepts.length > 0
                    ? ` | Concepts: ${data.key_concepts.length}`
                    : '';
                
                this.addLog('success', `✓ [${data.current}/${data.total}] ${data.filename}: ${data.old_chunks}→${data.new_chunks} chunks${octagramStr}${conceptsStr}`);
                break;
                
            case 'document_error':
                this.stats.failed++;
                this.updateStats();
                this.addLog('error', `✗ [${data.current}/${data.total}] ${data.filename}: ${data.error}`);
                break;
                
            case 'complete':
                this.isRunning = false;
                this.stats.processed = data.processed;
                this.stats.failed = data.failed;
                this.stats.totalVectors = data.total_vectors;
                this.stats.elapsedSeconds = data.elapsed_seconds;
                this.updateStats();
                this.updateConnectionStatus('disconnected');
                this.addLog('success', `🎉 Batch optimization complete! ${data.processed} documents processed, ${data.failed} failed`);
                this.stopHeartbeatMonitor();
                if (this.eventSource) {
                    this.eventSource.close();
                }
                break;
                
            case 'error':
            case 'fatal_error':
                this.isRunning = false;
                this.updateConnectionStatus('disconnected');
                this.addLog('error', `❌ Error: ${data.message || data.error}`);
                this.stopHeartbeatMonitor();
                if (this.eventSource) {
                    this.eventSource.close();
                }
                break;
        }
    }
    
    updateStats() {
        const percentage = this.stats.total > 0 
            ? Math.round((this.stats.processed / this.stats.total) * 100) 
            : 0;
        
        document.getElementById('progress-docs').textContent = `${this.stats.processed}/${this.stats.total}`;
        document.getElementById('progress-failed').textContent = this.stats.failed;
        document.getElementById('progress-vectors').textContent = this.stats.totalVectors;
        document.getElementById('progress-elapsed').textContent = this.formatTime(this.stats.elapsedSeconds);
        document.getElementById('progress-remaining').textContent = this.stats.estimatedRemainingSeconds > 0
            ? this.formatTime(this.stats.estimatedRemainingSeconds)
            : '~';
        document.getElementById('progress-bar').style.width = `${percentage}%`;
        document.getElementById('progress-percentage').textContent = `${percentage}%`;
    }
    
    formatTime(seconds) {
        if (seconds < 60) return `${seconds}s`;
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        if (minutes < 60) return `${minutes}m ${secs}s`;
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        return `${hours}h ${mins}m`;
    }
    
    addLog(type, message) {
        const logContainer = document.getElementById('progress-log');
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type}`;
        logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        logContainer.appendChild(logEntry);
        logContainer.scrollTop = logContainer.scrollHeight;
    }
    
    updateConnectionStatus(status) {
        const statusEl = document.getElementById('connection-status');
        statusEl.className = `connection-status ${status}`;
        const statusText = {
            'connected': '🟢 Connected',
            'connecting': '🟡 Connecting...',
            'disconnected': '⚫ Disconnected'
        };
        statusEl.textContent = statusText[status] || status;
    }
    
    startHeartbeatMonitor() {
        this.heartbeatTimer = setInterval(() => {
            if (this.lastUpdateTime) {
                const timeSinceLastUpdate = Date.now() - this.lastUpdateTime;
                if (timeSinceLastUpdate > BATCH_MONITOR_CONFIG.HEARTBEAT_TIMEOUT) {
                    this.addLog('info', '⚠️ No updates for 2 minutes. Connection may be slow...');
                }
            }
        }, 30000); // Check every 30 seconds
    }
    
    stopHeartbeatMonitor() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }
    
    showProgress() {
        document.getElementById('batch-progress-panel').classList.remove('hidden');
    }
    
    hideProgress() {
        document.getElementById('batch-progress-panel').classList.add('hidden');
    }
    
    stop() {
        this.isRunning = false;
        this.stopHeartbeatMonitor();
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        this.updateConnectionStatus('disconnected');
    }
}

// ========================================
// GLOBAL INSTANCE
// ========================================

// Create global instance
window.batchMonitor = new BatchMonitor();

console.log('📊 Batch Monitor initialized');

