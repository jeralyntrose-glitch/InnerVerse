const app = {
    currentProject: null,
    currentConversation: null,
    projects: [],
    modalCallback: null,
    sidebarOpen: true,
    currentTab: 'home',
    activityCache: null,
    activityCacheTime: null,
    isMobile: false,
    // Performance: Cache DOM elements
    cachedElements: {},
    
    getElement(id) {
        if (!this.cachedElements[id]) {
            this.cachedElements[id] = document.getElementById(id);
        }
        return this.cachedElements[id];
    },
    
    clearElementCache() {
        this.cachedElements = {};
    },

    // Offline resilience - localStorage persistence for PWA
    savePendingMessage(conversationId, message) {
        const pending = this.getPendingMessages();
        const messageId = `${conversationId}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        pending.push({
            id: messageId,
            conversationId,
            message,
            timestamp: Date.now(),
            status: 'pending'
        });
        localStorage.setItem('innerverse_pending_messages', JSON.stringify(pending));
        return messageId;
    },

    markMessageFailed(messageId) {
        const pending = this.getPendingMessages();
        const item = pending.find(p => p.id === messageId);
        if (item) {
            item.status = 'failed';
            localStorage.setItem('innerverse_pending_messages', JSON.stringify(pending));
        }
    },

    removePendingMessage(messageId) {
        let pending = this.getPendingMessages();
        pending = pending.filter(p => p.id !== messageId);
        localStorage.setItem('innerverse_pending_messages', JSON.stringify(pending));
    },

    getPendingMessages() {
        try {
            const data = localStorage.getItem('innerverse_pending_messages');
            return data ? JSON.parse(data) : [];
        } catch (e) {
            console.error('Error reading pending messages:', e);
            return [];
        }
    },

    async checkPendingMessages() {
        const pending = this.getPendingMessages();
        const failed = pending.filter(p => p.status === 'failed' && p.conversationId === this.currentConversation);
        
        // Show retry UI for failed messages
        if (failed.length > 0 && this.currentConversation) {
            failed.forEach(item => {
                this.showRetryUI(item.id, item.message);
            });
        }
    },

    showRetryUI(messageId, message) {
        const container = this.getElement('messagesContainer');
        const typingIndicator = this.getElement('typingIndicator');
        
        if (!container) return;

        // Check if retry UI already exists for this specific message ID
        const existing = container.querySelector(`[data-message-id="${messageId}"]`);
        if (existing) return; // Don't duplicate

        const retryDiv = document.createElement('div');
        retryDiv.className = 'message-retry';
        retryDiv.dataset.messageId = messageId;
        
        // Build the retry UI safely
        const innerDiv = document.createElement('div');
        innerDiv.style.cssText = 'padding: 16px; background: var(--bg-sidebar); border: 1px solid var(--error); border-radius: 12px; margin: 8px 0;';
        
        const headerDiv = document.createElement('div');
        headerDiv.style.cssText = 'color: var(--error); font-weight: 500; margin-bottom: 8px; display: flex; align-items: center; gap: 8px;';
        headerDiv.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            Message failed to send
        `;
        
        const messageDiv = document.createElement('div');
        messageDiv.style.cssText = 'color: var(--text-secondary); font-size: 0.875rem; margin-bottom: 12px;';
        // Use textContent to prevent XSS
        messageDiv.textContent = message.length > 50 ? message.substring(0, 50) + '...' : message;
        
        const retryButton = document.createElement('button');
        retryButton.style.cssText = 'background: var(--accent); color: white; border: none; padding: 8px 16px; border-radius: 6px; font-size: 0.875rem; cursor: pointer; font-weight: 500;';
        retryButton.textContent = 'Retry sending';
        retryButton.onclick = () => this.retryMessage(messageId, message, retryDiv);
        
        innerDiv.appendChild(headerDiv);
        innerDiv.appendChild(messageDiv);
        innerDiv.appendChild(retryButton);
        retryDiv.appendChild(innerDiv);
        
        container.insertBefore(retryDiv, typingIndicator);
    },

    async retryMessage(messageId, message, retryElement) {
        // Remove retry UI
        if (retryElement) {
            retryElement.remove();
        }
        
        // Remove from localStorage
        this.removePendingMessage(messageId);
        
        // Set input value and trigger send
        const input = this.getElement('messageInput');
        if (input) {
            input.value = message;
            await this.sendMessage();
        }
    },

    async init() {
        this.detectMobile();
        // Show loading state immediately
        const sidebar = this.getElement('sidebar');
        if (sidebar) sidebar.style.opacity = '0';
        
        await this.loadProjects();
        this.renderSidebarProjects();
        this.showDefaultChatView();
        this.setupEventListeners();
        this.loadSidebarState();
        
        // Setup browser history navigation (back button support)
        this.setupBrowserHistory();
        
        // Setup app resume detection for PWA offline resilience
        this.setupAppResumeDetection();
        
        // Set initial history state
        history.replaceState({ view: 'home' }, '', '/claude');
        
        // Fade in sidebar after loading
        if (sidebar) {
            sidebar.style.transition = 'opacity 200ms ease';
            sidebar.style.opacity = '1';
        }
        
        // Auto-focus input on load (like ChatGPT/Claude)
        setTimeout(() => {
            const messageInput = this.getElement('messageInput');
            if (messageInput) {
                messageInput.focus();
            }
        }, 100); // Reduced from 300ms
    },

    setupBrowserHistory() {
        // Handle browser back/forward buttons
        window.addEventListener('popstate', async (event) => {
            if (!event.state) return;
            
            const state = event.state;
            
            if (state.view === 'home') {
                this.currentConversation = null;
                this.currentProject = null;
                document.getElementById('topBarTitle').textContent = 'InnerVerse - MBTI Master';
                this.showDefaultChatView();
            } else if (state.view === 'project') {
                this.currentProject = state.projectId;
                this.currentConversation = null;
                
                const topBarTitle = this.getElement('topBarTitle');
                if (topBarTitle) {
                    topBarTitle.textContent = state.projectName.split(' ').slice(1).join(' ');
                }
                
                const messagesContainer = this.getElement('messagesContainer');
                const welcomeScreen = this.getElement('welcomeScreen');
                const inputSuggestions = this.getElement('inputSuggestions');
                
                if (welcomeScreen) welcomeScreen.classList.add('hidden');
                if (inputSuggestions) inputSuggestions.classList.add('hidden');
                if (messagesContainer) {
                    messagesContainer.classList.remove('hidden');
                    messagesContainer.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">
                                <div style="width: 40px; height: 40px; border: 3px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
                            </div>
                            <p style="color: var(--text-secondary); margin-top: 16px;">Loading conversations...</p>
                        </div>
                    `;
                }
                
                await this.loadConversationsAndRender();
                this.updateActiveProject();
            } else if (state.view === 'conversation') {
                this.currentConversation = state.conversationId;
                this.currentProject = state.projectId;
                
                const currentProjectObj = this.projects.find(p => p.id === state.projectId);
                const projectPrefix = currentProjectObj ? `${currentProjectObj.emoji} ` : '';
                document.getElementById('topBarTitle').textContent = `${projectPrefix}${state.conversationName}`;
                
                const welcomeScreen = document.getElementById('welcomeScreen');
                const messagesContainer = document.getElementById('messagesContainer');
                
                if (welcomeScreen) welcomeScreen.classList.add('hidden');
                if (messagesContainer) {
                    messagesContainer.classList.remove('hidden');
                    messagesContainer.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">
                                <div style="width: 40px; height: 40px; border: 3px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
                            </div>
                            <p style="color: var(--text-secondary); margin-top: 16px;">Loading...</p>
                        </div>
                    `;
                }
                
                try {
                    const response = await fetch(`/claude/conversations/detail/${state.conversationId}`);
                    const data = await response.json();
                    this.renderMessages(data.messages);
                    this.checkPendingMessages();
                } catch (error) {
                    console.error('Error loading conversation:', error);
                }
            }
        });
    },

    setupAppResumeDetection() {
        // Detect when user returns to app (critical for iOS PWA)
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.currentConversation) {
                // User returned to app - check for failed messages
                setTimeout(() => {
                    this.checkPendingMessages();
                }, 500); // Small delay to let UI settle
            }
        });

        // Also check on page load/reload
        window.addEventListener('pageshow', (event) => {
            if (event.persisted && this.currentConversation) {
                // Page restored from cache
                this.checkPendingMessages();
            }
        });
    },

    detectMobile() {
        this.isMobile = window.innerWidth < 768;
        if (this.isMobile) {
            this.sidebarOpen = false;
            document.getElementById('sidebar').classList.add('hidden');
        }
        
        window.addEventListener('resize', () => {
            const wasMobile = this.isMobile;
            this.isMobile = window.innerWidth < 768;
            
            if (wasMobile && !this.isMobile && !this.sidebarOpen) {
                this.sidebarOpen = true;
                document.getElementById('sidebar').classList.remove('hidden');
            }
        });
    },

    switchTab(tabName) {
        this.currentTab = tabName;
        
        // Close sidebar on mobile for Home and Activity tabs only
        // Keep sidebar open for Projects tab so user can pick a project
        if (this.isMobile && this.sidebarOpen && (tabName === 'home' || tabName === 'activity')) {
            this.toggleSidebar();
        }
        
        // Update tab buttons - add instant visual feedback
        document.querySelectorAll('.sidebar-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        const activeTab = document.getElementById(`tab${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`);
        if (activeTab) {
            activeTab.classList.add('active');
            // Instant visual feedback
            activeTab.style.transform = 'scale(0.95)';
            setTimeout(() => { activeTab.style.transform = ''; }, 100);
        }
        
        // Update sidebar tab content
        document.querySelectorAll('.sidebar-tab-content').forEach(content => {
            content.classList.add('hidden');
        });
        document.getElementById(`tabContent${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`).classList.remove('hidden');
        
        // Update main chat area based on tab
        if (tabName === 'home') {
            this.showHomeView();
        } else if (tabName === 'activity') {
            this.showActivityView();
        }
        // 'projects' tab just switches sidebar content, doesn't change main area
    },
    
    showHomeView() {
        // Reset to home: clear current conversation and project, show welcome screen
        this.currentConversation = null;
        this.currentProject = null;
        document.getElementById('topBarTitle').textContent = 'InnerVerse - MBTI Master';
        
        // Push browser history state
        history.pushState({ view: 'home' }, '', '/claude');
        
        this.showDefaultChatView();
    },
    
    async showActivityView() {
        // Show recent activity across all projects
        const messagesContainer = this.getElement('messagesContainer');
        const welcomeScreen = this.getElement('welcomeScreen');
        const inputSuggestions = this.getElement('inputSuggestions');
        const topBarTitle = this.getElement('topBarTitle');
        
        if (welcomeScreen) welcomeScreen.classList.add('hidden');
        if (inputSuggestions) inputSuggestions.classList.add('hidden');
        if (topBarTitle) topBarTitle.textContent = 'Recent Activity';
        
        if (messagesContainer) {
            messagesContainer.classList.remove('hidden');
            // Show instant loading spinner
            messagesContainer.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">
                        <div style="width: 40px; height: 40px; border: 3px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
                    </div>
                    <p style="color: var(--text-secondary); margin-top: 16px;">Loading recent activity...</p>
                </div>
            `;
            
            try {
                // Check cache first (cache for 30 seconds)
                const now = Date.now();
                if (this.activityCache && this.activityCacheTime && (now - this.activityCacheTime < 30000)) {
                    // Use cached data
                    messagesContainer.innerHTML = this.activityCache;
                    return;
                }
                
                // Fetch conversations from all projects in parallel for better performance
                const fetchPromises = this.projects.map(async (project) => {
                    try {
                        const response = await fetch(`/claude/conversations/${project.id}`);
                        const data = await response.json();
                        const conversations = data.conversations || [];
                        
                        // Add project info to each conversation
                        conversations.forEach(conv => {
                            conv.project_emoji = project.emoji;
                            conv.project_name = project.name.replace(project.emoji, '').trim();
                            conv.project_id = project.id;
                        });
                        
                        return conversations;
                    } catch (err) {
                        console.error(`Error loading conversations for ${project.name}:`, err);
                        return []; // Return empty array on error to keep Promise.all working
                    }
                });
                
                // Wait for all fetches to complete in parallel
                const projectConversations = await Promise.all(fetchPromises);
                
                // Flatten the array of arrays
                const allConversations = projectConversations.flat();
                
                // Sort by updated_at (most recent first)
                allConversations.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
                
                // Take only the 20 most recent
                const recentConversations = allConversations.slice(0, 20);
                
                if (recentConversations.length === 0) {
                    messagesContainer.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">
                                <svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="10"></circle>
                                    <polyline points="12 6 12 12 16 14"></polyline>
                                </svg>
                            </div>
                            <h2>No Recent Activity</h2>
                            <p style="color: var(--text-secondary); margin-top: 8px;">Start a conversation to see activity here!</p>
                        </div>
                    `;
                } else {
                    let html = '<div style="padding: 32px 24px; max-width: 800px; margin: 0 auto;">';
                    
                    // Header section - Claude style with larger, bolder text
                    html += '<h1 style="font-size: 2.125rem; font-weight: 700; margin-bottom: 32px; color: var(--text-primary); letter-spacing: -0.02em;">Your chat history</h1>';
                    
                    // Search bar - Claude style with blue outline on focus
                    html += `
                        <div style="margin-bottom: 24px;">
                            <div style="position: relative;">
                                <svg style="position: absolute; left: 16px; top: 50%; transform: translateY(-50%); color: var(--text-secondary);" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="11" cy="11" r="8"></circle>
                                    <path d="m21 21-4.35-4.35"></path>
                                </svg>
                                <input type="text" 
                                       id="activitySearch" 
                                       placeholder="Search your chats..." 
                                       style="width: 100%; padding: 13px 16px 13px 44px; border: 1.5px solid var(--border); border-radius: 12px; background: var(--bg-app); color: var(--text-primary); font-size: 0.9375rem; outline: none; transition: all 150ms ease; box-shadow: 0 1px 2px rgba(0,0,0,0.05);"
                                       onfocus="this.style.borderColor='var(--accent)'; this.style.boxShadow='0 0 0 3px var(--accent-light)';"
                                       onblur="this.style.borderColor='var(--border)'; this.style.boxShadow='0 1px 2px rgba(0,0,0,0.05)';"
                                       oninput="app.filterActivityChats(this.value)">
                            </div>
                        </div>
                    `;
                    
                    // Chat count - cleaner styling
                    html += `<div style="margin-bottom: 20px; color: var(--text-secondary); font-size: 0.875rem; font-weight: 500;">
                        ${recentConversations.length} conversation${recentConversations.length !== 1 ? 's' : ''}
                    </div>`;
                    
                    // Simple conversation list - ChatGPT style
                    html += '<div id="activityChatList" style="display: flex; flex-direction: column; gap: 2px;">';
                    recentConversations.forEach(conv => {
                        const date = new Date(conv.updated_at);
                        const timeAgo = this.getTimeAgo(date);
                        const projectFullName = `${conv.project_emoji} ${conv.project_name}`;
                        
                        html += `
                            <div class="activity-chat-card" data-search-text="${this.escapeHtml(conv.name).toLowerCase()} ${this.escapeHtml(conv.project_name).toLowerCase()}"
                                 style="display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border-radius: 8px; cursor: pointer; transition: background-color 100ms ease; gap: 12px;"
                                 onmouseover="this.style.background='var(--bg-hover)';"
                                 onmouseout="this.style.background='transparent';">
                                <div onclick='app.openProject(${JSON.stringify(conv.project_id)}, ${JSON.stringify(projectFullName)}); setTimeout(() => app.openConversation(${JSON.stringify(conv.id)}, ${JSON.stringify(conv.name)}), 100);' 
                                     style="flex: 1; min-width: 0; overflow: hidden; display: flex; align-items: center; gap: 8px;">
                                    <div style="font-size: 0.9375rem; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${this.escapeHtml(conv.name)}</div>
                                    <span style="font-size: 0.75rem; color: var(--text-tertiary); white-space: nowrap;">${timeAgo}</span>
                                </div>
                                <button onclick="event.stopPropagation(); if(confirm('Delete \\\"${this.escapeHtml(conv.name).replace(/"/g, '&quot;')}\\\"?')) app.deleteConversationById(${conv.id});"
                                        style="width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; border-radius: 6px; border: none; background: transparent; color: var(--text-tertiary); cursor: pointer; transition: all 100ms ease; padding: 0; flex-shrink: 0;"
                                        onmouseover="this.style.background='var(--bg-hover)'; this.style.color='var(--error)';"
                                        onmouseout="this.style.background='transparent'; this.style.color='var(--text-tertiary)';">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                        <polyline points="3 6 5 6 21 6"></polyline>
                                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                    </svg>
                                </button>
                            </div>
                        `;
                    });
                    html += '</div>'; // Close activityChatList
                    
                    html += '</div>';
                    messagesContainer.innerHTML = html;
                    
                    // Cache the result
                    this.activityCache = html;
                    this.activityCacheTime = Date.now();
                }
            } catch (error) {
                console.error('Error loading activity:', error);
                messagesContainer.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">⚠️</div>
                        <h2>Error loading activity</h2>
                        <p style="color: var(--text-secondary); margin-top: 8px;">Please try again.</p>
                    </div>
                `;
            }
        }
    },
    
    getTimeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(seconds / 3600);
        const days = Math.floor(seconds / 86400);
        
        if (seconds < 60) return 'just now';
        if (minutes === 1) return '1 minute ago';
        if (minutes < 60) return `${minutes} minutes ago`;
        if (hours === 1) return '1 hour ago';
        if (hours < 24) return `${hours} hours ago`;
        if (days === 1) return '1 day ago';
        if (days < 7) return `${days} days ago`;
        
        return date.toLocaleDateString();
    },
    
    filterActivityChats(searchText) {
        const chatCards = document.querySelectorAll('.activity-chat-card');
        const lowerSearch = searchText.toLowerCase();
        
        chatCards.forEach(card => {
            const cardText = card.getAttribute('data-search-text') || '';
            if (cardText.includes(lowerSearch)) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    },

    formatTimestamp(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        // ChatGPT-style timestamps
        if (diffMins < 1) return 'now';
        if (diffMins < 60) return `${diffMins}m`;
        if (diffHours < 24) return `${diffHours}h`;
        if (diffDays < 7) return `${diffDays}d`;
        
        // Format as MMM D for older dates
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return `${months[date.getMonth()]} ${date.getDate()}`;
    },

    setupChatListHoverEffects() {
        const container = this.getElement('messagesContainer');
        if (!container) return;
        
        container.addEventListener('mouseover', (e) => {
            const item = e.target.closest('.chat-list-item');
            if (item && !item.classList.contains('active-chat')) {
                item.style.background = 'var(--bg-hover)';
            }
        });
        
        container.addEventListener('mouseout', (e) => {
            const item = e.target.closest('.chat-list-item');
            if (item && !item.classList.contains('active-chat')) {
                item.style.background = 'transparent';
            }
        });
    },

    async deleteConversationWithConfirm(conversationId, conversationName) {
        const confirmed = confirm(`Delete "${conversationName}"?\n\nThis cannot be undone.`);
        if (!confirmed) return;
        
        try {
            await fetch(`/claude/conversations/${conversationId}`, {
                method: 'DELETE'
            });
            
            // Reload conversation list
            await this.renderProjectChatView();
            
            // If we deleted the current conversation, go back to welcome
            if (this.currentConversation === conversationId) {
                this.currentConversation = null;
                this.showDefaultChatView();
            }
        } catch (error) {
            console.error('Error deleting conversation:', error);
            alert('Failed to delete conversation. Please try again.');
        }
    },

    closeSidebar() {
        if (this.isMobile) {
            this.sidebarOpen = false;
            document.getElementById('sidebar').classList.add('hidden');
            document.getElementById('sidebarBackdrop').classList.remove('visible');
            document.body.classList.remove('sidebar-open');
            localStorage.setItem('sidebarOpen', false);
        }
    },

    async startChatWithPrompt(prompt) {
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.value = prompt;
            messageInput.style.height = 'auto';
            const newHeight = Math.min(messageInput.scrollHeight, 120);
            messageInput.style.height = newHeight + 'px';
            
            // Close sidebar on mobile
            if (this.isMobile) {
                this.closeSidebar();
            }
            
            // Auto-send the message
            await this.sendMessage();
        }
    },

    setupEventListeners() {
        const hamburgerBtn = document.getElementById('hamburgerBtn');
        if (hamburgerBtn) {
            hamburgerBtn.addEventListener('click', () => {
                this.toggleSidebar();
            });
        }

        const uploadBtn = document.getElementById('uploadBtn');
        const fileInput = document.getElementById('fileInput');
        if (uploadBtn && fileInput) {
            uploadBtn.addEventListener('click', () => {
                fileInput.click();
            });

            fileInput.addEventListener('change', (e) => {
                const files = e.target.files;
                if (files && files.length > 0) {
                    console.log('Files selected:', Array.from(files).map(f => f.name));
                    alert(`Selected ${files.length} file(s): ${Array.from(files).map(f => f.name).join(', ')}\n\nFile upload functionality coming soon!`);
                }
            });
        }

        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });

            // Debounced auto-expand for better performance
            let resizeTimeout;
            messageInput.addEventListener('input', () => {
                // Clear previous timeout
                clearTimeout(resizeTimeout);
                
                // Immediate resize for better UX
                messageInput.style.height = 'auto';
                const newHeight = Math.min(messageInput.scrollHeight, 120);
                messageInput.style.height = newHeight + 'px';
                
                // Debounced scrollbar update
                resizeTimeout = setTimeout(() => {
                    if (messageInput.scrollHeight > 120) {
                        messageInput.style.overflowY = 'auto';
                    } else {
                        messageInput.style.overflowY = 'hidden';
                    }
                }, 50);
            });
        }

        const modalInput = document.getElementById('modalInput');
        if (modalInput) {
            modalInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.submitModal();
                }
            });
        }

        if (window.innerWidth <= 768) {
            this.sidebarOpen = false;
            document.getElementById('sidebar').classList.add('hidden');
        }
    },

    loadSidebarState() {
        const savedState = localStorage.getItem('sidebarOpen');
        if (savedState !== null) {
            this.sidebarOpen = savedState === 'true';
            const sidebar = document.getElementById('sidebar');
            if (!this.sidebarOpen) {
                sidebar.classList.add('hidden');
            }
        }
    },

    toggleSidebar() {
        this.sidebarOpen = !this.sidebarOpen;
        const sidebar = document.getElementById('sidebar');
        const backdrop = document.getElementById('sidebarBackdrop');
        
        if (this.sidebarOpen) {
            sidebar.classList.remove('hidden');
            if (this.isMobile) {
                backdrop.classList.add('visible');
                document.body.classList.add('sidebar-open');
            }
        } else {
            sidebar.classList.add('hidden');
            if (this.isMobile) {
                backdrop.classList.remove('visible');
                document.body.classList.remove('sidebar-open');
            }
        }
        
        localStorage.setItem('sidebarOpen', this.sidebarOpen);
    },

    async loadProjects() {
        try {
            const response = await fetch('/claude/projects');
            const data = await response.json();
            this.projects = data.projects;
        } catch (error) {
            console.error('Error loading projects:', error);
            this.projects = [];
        }
    },

    renderSidebarProjects() {
        const container = document.getElementById('sidebarProjects');
        if (!container) return;

        container.innerHTML = '';

        this.projects.forEach(project => {
            const projectItem = document.createElement('div');
            projectItem.className = 'project-item';
            
            const emojiDiv = document.createElement('div');
            emojiDiv.className = 'project-emoji';
            emojiDiv.textContent = project.emoji;
            
            const nameDiv = document.createElement('div');
            nameDiv.className = 'project-name';
            nameDiv.textContent = project.name.replace(project.emoji, '').trim();
            
            projectItem.appendChild(emojiDiv);
            projectItem.appendChild(nameDiv);
            
            projectItem.addEventListener('click', () => {
                this.openProject(project.id, project.name);
            });
            
            container.appendChild(projectItem);
        });
    },

    showDefaultChatView() {
        // Show welcome screen, hide messages container
        const welcomeScreen = document.getElementById('welcomeScreen');
        const messagesContainer = document.getElementById('messagesContainer');
        const inputSuggestions = document.getElementById('inputSuggestions');
        
        if (welcomeScreen) {
            welcomeScreen.classList.remove('hidden');
        }
        if (messagesContainer) {
            messagesContainer.classList.add('hidden');
            messagesContainer.innerHTML = '';
        }
        if (inputSuggestions) {
            inputSuggestions.classList.remove('hidden');
        }
    },

    async openProject(projectId, projectName) {
        this.currentProject = projectId;
        this.currentConversation = null;
        
        // Push browser history state
        history.pushState({ view: 'project', projectId, projectName }, '', `/claude?project=${projectId}`);
        
        // Instant visual feedback
        const topBarTitle = this.getElement('topBarTitle');
        if (topBarTitle) {
            topBarTitle.textContent = projectName.split(' ').slice(1).join(' ');
        }
        
        // Show loading state immediately
        const messagesContainer = this.getElement('messagesContainer');
        const welcomeScreen = this.getElement('welcomeScreen');
        const inputSuggestions = this.getElement('inputSuggestions');
        
        if (welcomeScreen) welcomeScreen.classList.add('hidden');
        if (inputSuggestions) inputSuggestions.classList.add('hidden');
        if (messagesContainer) {
            messagesContainer.classList.remove('hidden');
            messagesContainer.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">
                        <div style="width: 40px; height: 40px; border: 3px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
                    </div>
                    <p style="color: var(--text-secondary); margin-top: 16px;">Loading conversations...</p>
                </div>
            `;
        }
        
        // Load conversations (single fetch, instant render)
        await this.loadConversationsAndRender();
        
        this.updateActiveProject();
        
        // Close sidebar on mobile after opening project
        if (window.innerWidth <= 768 && this.sidebarOpen) {
            this.closeSidebar();
        }
    },

    async renderProjectChatView() {
        // When opening a project, show conversation list
        const welcomeScreen = document.getElementById('welcomeScreen');
        const messagesContainer = document.getElementById('messagesContainer');
        const inputSuggestions = document.getElementById('inputSuggestions');
        
        if (welcomeScreen) welcomeScreen.classList.add('hidden');
        if (inputSuggestions) inputSuggestions.classList.add('hidden');
        if (messagesContainer) {
            messagesContainer.classList.remove('hidden');
            
            // Fetch conversations for this project
            try {
                const response = await fetch(`/claude/conversations/${this.currentProject}`);
                const data = await response.json();
                const conversations = data.conversations || [];
                
                // Show conversation list view
                if (conversations.length === 0) {
                    messagesContainer.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">
                                <svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                                </svg>
                            </div>
                            <h2>No conversations yet</h2>
                            <p style="color: var(--text-secondary); margin-top: 8px;">Start a new conversation to begin chatting!</p>
                        </div>
                    `;
                } else {
                    // ChatGPT-style conversation list - compact and clean
                    const grouped = this.groupConversationsByDate(conversations);
                    
                    let html = '<div style="padding: 12px 8px; max-width: 800px; margin: 0 auto;">';
                    
                    Object.entries(grouped).forEach(([dateLabel, convs]) => {
                        if (convs.length === 0) return;
                        
                        html += `<div style="margin-bottom: 16px;">`;
                        html += `<div style="font-size: 0.75rem; color: var(--text-tertiary); font-weight: 600; padding: 0 12px; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.05em;">${dateLabel}</div>`;
                        
                        convs.forEach(conv => {
                            const timestamp = this.formatTimestamp(conv.updated_at);
                            const preview = conv.name.length > 60 ? conv.name.substring(0, 60) + '...' : conv.name;
                            const isActive = this.currentConversation === conv.id;
                            const activeClass = isActive ? ' active-chat' : '';
                            const activeBg = isActive ? 'var(--bg-active)' : 'transparent';
                            
                            html += `
                                <div class="chat-list-item${activeClass}" 
                                     data-conv-id="${conv.id}"
                                     data-conv-name="${this.escapeHtml(conv.name)}"
                                     style="padding: 10px 12px; margin-bottom: 4px; background: ${activeBg}; border-radius: 8px; cursor: pointer; transition: background-color 100ms ease; position: relative; overflow: hidden;">
                                    <div class="chat-item-content" 
                                         onclick='app.openConversation(${JSON.stringify(conv.id)}, ${JSON.stringify(conv.name)})'
                                         style="display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; position: relative; z-index: 2;">
                                        <div style="flex: 1; min-width: 0; overflow: hidden;">
                                            <div style="font-size: 0.9375rem; color: var(--text-primary); font-weight: 400; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                                ${this.escapeHtml(preview)}
                                            </div>
                                        </div>
                                        <div style="display: flex; align-items: center; gap: 8px; flex-shrink: 0;">
                                            <span style="font-size: 0.75rem; color: var(--text-tertiary); white-space: nowrap;">${timestamp}</span>
                                            <button class="chat-delete-btn" 
                                                    onclick="event.stopPropagation(); app.deleteConversationWithConfirm('${conv.id}', '${this.escapeHtml(conv.name).replace(/'/g, "\\'")}')"
                                                    style="width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; border-radius: 6px; border: none; background: transparent; color: var(--text-tertiary); cursor: pointer; transition: all 100ms ease; padding: 0;"
                                                    onmouseover="this.style.background='var(--bg-hover)'; this.style.color='var(--error)';"
                                                    onmouseout="this.style.background='transparent'; this.style.color='var(--text-tertiary)';">
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                                    <polyline points="3 6 5 6 21 6"></polyline>
                                                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                                </svg>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            `;
                        });
                        
                        html += '</div>';
                    });
                    
                    html += '</div>';
                    messagesContainer.innerHTML = html;
                    
                    // Add hover effects via event delegation
                    this.setupChatListHoverEffects();
                }
            } catch (error) {
                console.error('Error loading conversations:', error);
                messagesContainer.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">⚠️</div>
                        <h2>Error loading conversations</h2>
                        <p style="color: var(--text-secondary); margin-top: 8px;">Please try again.</p>
                    </div>
                `;
            }
        }
    },

    renderProjectChatViewOLD() {
        const messagesContainer = document.getElementById('messagesContainer');
        if (!messagesContainer) return;

        messagesContainer.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">
                    <svg width="80" height="80" viewBox="0 0 200 200" class="brain-icon-animated">
                        <defs>
                            <linearGradient id="brainGradientProject" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" style="stop-color:#8b5cf6;stop-opacity:1" />
                                <stop offset="100%" style="stop-color:#06b6d4;stop-opacity:1" />
                            </linearGradient>
                        </defs>
                        <g class="brain-network">
                            <line x1="60" y1="50" x2="100" y2="80" stroke="url(#brainGradientProject)" stroke-width="2" opacity="0.6"/>
                            <line x1="140" y1="50" x2="100" y2="80" stroke="url(#brainGradientProject)" stroke-width="2" opacity="0.6"/>
                            <line x1="60" y1="50" x2="100" y2="120" stroke="url(#brainGradientProject)" stroke-width="2" opacity="0.6"/>
                            <line x1="140" y1="50" x2="100" y2="120" stroke="url(#brainGradientProject)" stroke-width="2" opacity="0.6"/>
                            <line x1="40" y1="100" x2="100" y2="80" stroke="url(#brainGradientProject)" stroke-width="2" opacity="0.6"/>
                            <line x1="160" y1="100" x2="100" y2="80" stroke="url(#brainGradientProject)" stroke-width="2" opacity="0.6"/>
                            <line x1="40" y1="100" x2="100" y2="120" stroke="url(#brainGradientProject)" stroke-width="2" opacity="0.6"/>
                            <line x1="160" y1="100" x2="100" y2="120" stroke="url(#brainGradientProject)" stroke-width="2" opacity="0.6"/>
                            <line x1="60" y1="150" x2="100" y2="120" stroke="url(#brainGradientProject)" stroke-width="2" opacity="0.6"/>
                            <line x1="140" y1="150" x2="100" y2="120" stroke="url(#brainGradientProject)" stroke-width="2" opacity="0.6"/>
                            <circle cx="60" cy="50" r="8" fill="url(#brainGradientProject)" opacity="0.9"/>
                            <circle cx="140" cy="50" r="8" fill="url(#brainGradientProject)" opacity="0.9"/>
                            <circle cx="40" cy="100" r="8" fill="url(#brainGradientProject)" opacity="0.9"/>
                            <circle cx="100" cy="80" r="10" fill="url(#brainGradientProject)"/>
                            <circle cx="100" cy="120" r="10" fill="url(#brainGradientProject)"/>
                            <circle cx="160" cy="100" r="8" fill="url(#brainGradientProject)" opacity="0.9"/>
                            <circle cx="60" cy="150" r="8" fill="url(#brainGradientProject)" opacity="0.9"/>
                            <circle cx="140" cy="150" r="8" fill="url(#brainGradientProject)" opacity="0.9"/>
                        </g>
                    </svg>
                </div>
                <p>Start a new conversation or select one from the sidebar!</p>
            </div>
        `;
    },

    updateActiveProject() {
        document.querySelectorAll('.project-item').forEach((item, index) => {
            if (this.projects[index]?.id === this.currentProject) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    },

    async loadConversations() {
        if (!this.currentProject) return;

        try {
            const response = await fetch(`/claude/conversations/${this.currentProject}`);
            const data = await response.json();
            this.renderSidebarConversations(data.conversations);
        } catch (error) {
            console.error('Error loading conversations:', error);
        }
    },

    async loadConversationsAndRender() {
        if (!this.currentProject) {
            console.warn('loadConversationsAndRender: No current project set');
            return;
        }

        console.log(`🔍 loadConversationsAndRender: Loading conversations for project "${this.currentProject}"`);

        try {
            const response = await fetch(`/claude/conversations/${this.currentProject}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const data = await response.json();
            const conversations = data.conversations || [];
            
            console.log(`✅ Loaded ${conversations.length} conversations for project "${this.currentProject}"`);
            
            // Update sidebar
            this.renderSidebarConversations(conversations);
            
            // Render main chat area instantly
            const messagesContainer = this.getElement('messagesContainer');
            if (!messagesContainer) {
                console.error('❌ messagesContainer element not found!');
                return;
            }
            
            if (conversations.length === 0) {
                messagesContainer.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">
                            <svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                            </svg>
                        </div>
                        <h2>No conversations yet</h2>
                        <p style="color: var(--text-secondary); margin-top: 8px;">Start a new conversation to begin chatting!</p>
                    </div>
                `;
            } else {
                // ChatGPT-style conversation list - compact and clean
                const grouped = this.groupConversationsByDate(conversations);
                
                let html = '<div style="padding: 12px 8px; max-width: 800px; margin: 0 auto;">';
                
                Object.entries(grouped).forEach(([dateLabel, convs]) => {
                    if (convs.length === 0) return;
                    
                    html += `<div style="margin-bottom: 16px;">`;
                    html += `<div style="font-size: 0.75rem; color: var(--text-tertiary); font-weight: 600; padding: 0 12px; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.05em;">${dateLabel}</div>`;
                    
                    convs.forEach(conv => {
                        const timestamp = this.formatTimestamp(conv.updated_at);
                        const preview = conv.name.length > 60 ? conv.name.substring(0, 60) + '...' : conv.name;
                        const isActive = this.currentConversation === conv.id;
                        const activeClass = isActive ? ' active-chat' : '';
                        const activeBg = isActive ? 'var(--bg-active)' : 'transparent';
                        
                        html += `
                            <div class="chat-list-item${activeClass}" 
                                 data-conv-id="${conv.id}"
                                 data-conv-name="${this.escapeHtml(conv.name)}"
                                 style="padding: 10px 12px; margin-bottom: 4px; background: ${activeBg}; border-radius: 8px; cursor: pointer; transition: background-color 100ms ease; position: relative; overflow: hidden;">
                                <div class="chat-item-content" 
                                     onclick='app.openConversation(${JSON.stringify(conv.id)}, ${JSON.stringify(conv.name)})'
                                     style="display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; position: relative; z-index: 2;">
                                    <div style="flex: 1; min-width: 0; overflow: hidden;">
                                        <div style="font-size: 0.9375rem; color: var(--text-primary); font-weight: 400; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                            ${this.escapeHtml(preview)}
                                        </div>
                                    </div>
                                    <div style="display: flex; align-items: center; gap: 8px; flex-shrink: 0;">
                                        <span style="font-size: 0.75rem; color: var(--text-tertiary); white-space: nowrap;">${timestamp}</span>
                                        <button class="chat-delete-btn" 
                                                onclick="event.stopPropagation(); app.deleteConversationWithConfirm('${conv.id}', '${this.escapeHtml(conv.name).replace(/'/g, "\\'")}')"
                                                style="width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; border-radius: 6px; border: none; background: transparent; color: var(--text-tertiary); cursor: pointer; transition: all 100ms ease; padding: 0;"
                                                onmouseover="this.style.background='var(--bg-hover)'; this.style.color='var(--error)';"
                                                onmouseout="this.style.background='transparent'; this.style.color='var(--text-tertiary)';">
                                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                                <polyline points="3 6 5 6 21 6"></polyline>
                                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                            </svg>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                    
                    html += '</div>';
                });
                
                html += '</div>';
                messagesContainer.innerHTML = html;
                
                // Add hover effects via event delegation
                this.setupChatListHoverEffects();
            }
        } catch (error) {
            console.error('Error loading conversations:', error);
            const messagesContainer = this.getElement('messagesContainer');
            if (messagesContainer) {
                messagesContainer.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">⚠️</div>
                        <h2>Error loading conversations</h2>
                        <p style="color: var(--text-secondary); margin-top: 8px;">Please try again.</p>
                    </div>
                `;
            }
        }
    },

    groupConversationsByDate(conversations) {
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        const sevenDaysAgo = new Date(today);
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
        const thirtyDaysAgo = new Date(today);
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

        const groups = {
            'Today': [],
            'Yesterday': [],
            'Previous 7 days': [],
            'Previous 30 days': [],
            'Older': []
        };

        conversations.forEach(conv => {
            const convDate = new Date(conv.created_at || conv.updated_at);
            const convDay = new Date(convDate.getFullYear(), convDate.getMonth(), convDate.getDate());

            if (convDay.getTime() === today.getTime()) {
                groups['Today'].push(conv);
            } else if (convDay.getTime() === yesterday.getTime()) {
                groups['Yesterday'].push(conv);
            } else if (convDate >= sevenDaysAgo) {
                groups['Previous 7 days'].push(conv);
            } else if (convDate >= thirtyDaysAgo) {
                groups['Previous 30 days'].push(conv);
            } else {
                groups['Older'].push(conv);
            }
        });

        return groups;
    },

    renderChatHistory(conversations) {
        const container = document.getElementById('chatHistoryList');
        if (!container) return;

        container.innerHTML = '';

        if (conversations.length === 0) {
            const emptyDiv = document.createElement('div');
            emptyDiv.style.padding = '20px';
            emptyDiv.style.textAlign = 'center';
            emptyDiv.style.color = 'var(--text-secondary)';
            emptyDiv.style.fontSize = '0.9rem';
            emptyDiv.textContent = 'No conversations yet';
            container.appendChild(emptyDiv);
            return;
        }

        const grouped = this.groupConversationsByDate(conversations);

        Object.entries(grouped).forEach(([dateLabel, convs]) => {
            if (convs.length === 0) return;

            const dateGroup = document.createElement('div');
            dateGroup.className = 'date-group';

            const label = document.createElement('div');
            label.className = 'date-label';
            label.textContent = dateLabel;
            dateGroup.appendChild(label);

            convs.forEach(conv => {
                const wrapper = document.createElement('div');
                wrapper.className = 'conversation-item-compact';
                wrapper.id = `conv-${conv.id}`;
                if (conv.id === this.currentConversation) {
                    wrapper.classList.add('active');
                }
                
                wrapper.addEventListener('click', () => {
                    this.openConversation(conv.id, conv.name);
                });

                const nameDiv = document.createElement('div');
                nameDiv.className = 'conversation-name-compact';
                nameDiv.textContent = conv.name || 'New Chat';
                
                const timestampDiv = document.createElement('div');
                timestampDiv.className = 'conversation-timestamp';
                timestampDiv.textContent = this.formatTimestamp(conv.updated_at || conv.created_at);
                
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'delete-btn-compact';
                deleteBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>';
                deleteBtn.title = 'Delete';
                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (confirm(`Delete "${conv.name}"?`)) {
                        this.deleteConversationById(conv.id);
                    }
                });
                
                wrapper.appendChild(nameDiv);
                wrapper.appendChild(timestampDiv);
                wrapper.appendChild(deleteBtn);

                dateGroup.appendChild(wrapper);
            });

            container.appendChild(dateGroup);
        });
    },

    renderSidebarConversations(conversations) {
        const section = document.getElementById('sidebarConversationsSection');
        const container = document.getElementById('sidebarConversations');
        
        if (!container) return;

        section.style.display = 'block';
        container.innerHTML = '';

        // For Activity tab, render chat history with date grouping
        this.renderChatHistory(conversations);

        if (conversations.length === 0) {
            const emptyDiv = document.createElement('div');
            emptyDiv.style.padding = '8px';
            emptyDiv.style.color = 'var(--text-secondary)';
            emptyDiv.style.fontSize = '0.85rem';
            emptyDiv.textContent = 'No conversations yet';
            container.appendChild(emptyDiv);
        } else {
            conversations.forEach(conv => {
                const wrapper = document.createElement('div');
                wrapper.className = 'conversation-item-wrapper';
                wrapper.id = `conv-${conv.id}`;
                if (conv.id === this.currentConversation) {
                    wrapper.classList.add('active');
                }
                
                const nameDiv = document.createElement('div');
                nameDiv.className = 'conversation-name-sidebar';
                nameDiv.textContent = conv.name;
                nameDiv.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.openConversation(conv.id, conv.name);
                });
                
                wrapper.addEventListener('click', () => {
                    this.openConversation(conv.id, conv.name);
                });
                
                const actionsDiv = document.createElement('div');
                actionsDiv.className = 'conversation-actions-sidebar';
                
                const renameBtn = document.createElement('button');
                renameBtn.className = 'icon-btn-small';
                renameBtn.title = 'Rename';
                renameBtn.textContent = '✏️';
                renameBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.renameConversationById(conv.id);
                });
                
                const moveBtn = document.createElement('button');
                moveBtn.className = 'icon-btn-small';
                moveBtn.title = 'Move to Project';
                moveBtn.textContent = '📁';
                moveBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.showMoveToProjectModal(conv.id, conv.name);
                });
                
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'icon-btn-small';
                deleteBtn.title = 'Delete';
                deleteBtn.textContent = '🗑️';
                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.deleteConversationById(conv.id);
                });
                
                actionsDiv.appendChild(renameBtn);
                actionsDiv.appendChild(moveBtn);
                actionsDiv.appendChild(deleteBtn);
                
                wrapper.appendChild(nameDiv);
                wrapper.appendChild(actionsDiv);
                container.appendChild(wrapper);
            });
        }
    },

    async quickNewChat() {
        if (!this.currentProject) {
            if (this.projects.length > 0) {
                await this.openProject(this.projects[0].id, this.projects[0].name);
            }
        }
        
        await this.createNewConversation();
    },

    async createNewConversation() {
        if (!this.currentProject) {
            alert('Please select a project first');
            return;
        }

        this.showModal('Name your conversation', 'e.g., ENFP-INFJ Golden Pair', async (name) => {
            if (!name || name.trim() === '') {
                alert('Please enter a conversation name');
                return;
            }

            try {
                const response = await fetch('/claude/conversations', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ project: this.currentProject, name })
                });

                const data = await response.json();
                await this.loadConversations();
                await this.openConversation(data.id, data.name);
            } catch (error) {
                console.error('Error creating conversation:', error);
                alert('Failed to create conversation');
            }
        });
    },

    async autoCreateConversation(firstMessage) {
        // If no project, select the first one or use a default
        if (!this.currentProject) {
            if (this.projects.length > 0) {
                await this.openProject(this.projects[0].id, this.projects[0].name);
            } else {
                // No projects exist, can't create conversation
                console.error('No projects available');
                return false;
            }
        }

        // Generate conversation name from first message (first 30 chars)
        const autoName = firstMessage.length > 30 
            ? firstMessage.substring(0, 30) + '...' 
            : firstMessage;

        try {
            const response = await fetch('/claude/conversations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project: this.currentProject, name: autoName })
            });

            const data = await response.json();
            await this.loadConversations();
            
            // Set as current conversation
            this.currentConversation = data.id;
            document.getElementById('topBarTitle').textContent = data.name;
            
            // Show messages container, hide welcome screen and suggestions
            const welcomeScreen = document.getElementById('welcomeScreen');
            const messagesContainer = document.getElementById('messagesContainer');
            const inputSuggestions = document.getElementById('inputSuggestions');
            if (welcomeScreen) welcomeScreen.classList.add('hidden');
            if (messagesContainer) {
                messagesContainer.classList.remove('hidden');
                messagesContainer.innerHTML = ''; // Clear any error messages or old content
            }
            if (inputSuggestions) inputSuggestions.classList.add('hidden');
            
            return true;
        } catch (error) {
            console.error('Error auto-creating conversation:', error);
            return false;
        }
    },

    async openConversation(conversationId, conversationName) {
        this.currentConversation = conversationId;
        
        // Push browser history state
        const currentProjectObj = this.projects.find(p => p.id === this.currentProject);
        history.pushState({ 
            view: 'conversation', 
            conversationId, 
            conversationName,
            projectId: this.currentProject,
            projectName: currentProjectObj?.name 
        }, '', `/claude?conversation=${conversationId}`);
        
        // Instant UI transition - no delays
        const moveBtn = document.getElementById('move-to-project-btn');
        if (moveBtn) moveBtn.style.display = 'flex';
        
        const projectPrefix = currentProjectObj ? `${currentProjectObj.emoji} ` : '';
        document.getElementById('topBarTitle').textContent = `${projectPrefix}${conversationName}`;
        
        const welcomeScreen = document.getElementById('welcomeScreen');
        const messagesContainer = document.getElementById('messagesContainer');
        
        // Instant transition
        if (welcomeScreen) welcomeScreen.classList.add('hidden');
        if (messagesContainer) {
            messagesContainer.classList.remove('hidden');
            // Show loading state immediately for instant feedback
            messagesContainer.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">
                        <div style="width: 40px; height: 40px; border: 3px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
                    </div>
                    <p style="color: var(--text-secondary); margin-top: 16px;">Loading...</p>
                </div>
            `;
        }

        document.querySelectorAll('.conversation-item-wrapper').forEach(item => {
            item.classList.remove('active');
        });
        document.getElementById(`conv-${conversationId}`)?.classList.add('active');

        // CLOSE sidebar on mobile (don't toggle - always close)
        if (window.innerWidth <= 768 && this.sidebarOpen) {
            this.closeSidebar();
        }

        // Load messages in background (non-blocking)
        try {
            const response = await fetch(`/claude/conversations/detail/${conversationId}`);
            const data = await response.json();
            this.renderMessages(data.messages);
            
            // Check for pending/failed messages (no delay needed)
            this.checkPendingMessages();
        } catch (error) {
            console.error('Error loading conversation:', error);
            if (messagesContainer) {
                messagesContainer.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">⚠️</div>
                        <h2>Error loading conversation</h2>
                        <p style="color: var(--text-secondary); margin-top: 8px;">Please try again.</p>
                    </div>
                `;
            }
        }
    },

    renderMessages(messages) {
        const container = document.getElementById('messagesContainer');
        const typingIndicator = document.getElementById('typingIndicator');
        
        if (!container) return;

        container.innerHTML = '';
        
        if (messages.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🧠</div>
                    <p>Start chatting about MBTI, cognitive functions, and type theory!</p>
                </div>
            `;
        } else {
            messages.forEach(msg => {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${msg.role}`;
                // For existing messages, show immediately without streaming
                messageDiv.innerHTML = this.formatMessage(msg.content);
                container.appendChild(messageDiv);
            });
        }

        if (typingIndicator) {
            container.appendChild(typingIndicator);
        }

        setTimeout(() => {
            const container = document.getElementById('messagesContainer');
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        }, 100);
    },

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    },

    formatMessage(content) {
        content = this.escapeHtml(content);
        
        content = content.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
        content = content.replace(/`([^`]+)`/g, '<code>$1</code>');
        content = content.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        content = content.replace(/\*(.+?)\*/g, '<em>$1</em>');
        content = content.replace(/\n/g, '<br>');
        return content;
    },
    
    async streamText(element, text, speed = 8) {
        // Display text with typewriter effect (like Claude/ChatGPT) - optimized
        const formatted = this.formatMessage(text);
        element.innerHTML = '';
        
        let currentIndex = 0;
        let scrollCounter = 0;
        
        const displayChunk = () => {
            if (currentIndex < formatted.length) {
                // Add characters in larger chunks for faster display
                const chunkSize = 5; // Increased from 3 to 5 for faster streaming
                const chunk = formatted.substring(currentIndex, currentIndex + chunkSize);
                element.innerHTML = formatted.substring(0, currentIndex + chunk.length);
                currentIndex += chunk.length;
                
                // Scroll less frequently for better performance (every 10 chunks)
                // Only scroll if user is near bottom (Claude-style smooth scrolling)
                scrollCounter++;
                if (scrollCounter % 10 === 0) {
                    this.scrollToBottomIfNeeded();
                }
                
                // Continue streaming with requestAnimationFrame for smoothness
                requestAnimationFrame(() => {
                    setTimeout(displayChunk, speed);
                });
            } else {
                // Final scroll when done
                this.scrollToBottom();
            }
        };
        
        displayChunk();
    },

    async sendMessage() {
        const input = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        const typingIndicator = document.getElementById('typingIndicator');
        
        if (!input || !sendBtn) return;
        
        const message = input.value.trim();
        if (!message) return;

        // Hide input suggestions (ChatGPT-style)
        const inputSuggestions = document.getElementById('inputSuggestions');
        if (inputSuggestions) {
            inputSuggestions.classList.add('hidden');
        }

        // Auto-create conversation if none exists
        if (!this.currentConversation) {
            await this.autoCreateConversation(message);
            if (!this.currentConversation) {
                // If auto-create failed, show error
                alert('Failed to create conversation. Please try again.');
                return;
            }
        }

        // Save to localStorage BEFORE sending (PWA offline resilience)
        const messageId = this.savePendingMessage(this.currentConversation, message);

        input.value = '';
        input.style.height = '40px'; // Reset to min-height
        input.style.overflowY = 'hidden';
        sendBtn.disabled = true;

        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'message user';
        userMessageDiv.textContent = message;
        
        const container = document.getElementById('messagesContainer');
        container.insertBefore(userMessageDiv, typingIndicator);
        this.scrollToBottom();

        // Show thinking indicator
        const thinkingIndicator = document.getElementById('thinkingIndicator');
        if (thinkingIndicator) {
            thinkingIndicator.classList.add('active');
        }

        if (typingIndicator) {
            typingIndicator.classList.add('active');
        }

        try {
            const response = await fetch(`/claude/conversations/${this.currentConversation}/message`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            // Success - remove from localStorage
            this.removePendingMessage(messageId);

            // Hide thinking indicator
            if (thinkingIndicator) {
                thinkingIndicator.classList.remove('active');
            }

            if (typingIndicator) {
                typingIndicator.classList.remove('active');
            }

            // Create assistant message div and stream text into it
            const assistantMessageDiv = document.createElement('div');
            assistantMessageDiv.className = 'message assistant';
            container.insertBefore(assistantMessageDiv, typingIndicator);
            
            // Claude-style: Create space by scrolling before streaming starts
            // This pushes user message up, creating stable room for AI response
            this.scrollToBottom();
            
            // Stream the response with typewriter effect
            await this.streamText(assistantMessageDiv, data.assistant_message.content, 10);
            this.scrollToBottom();
        } catch (error) {
            console.error('Error sending message:', error);
            
            // Mark as failed in localStorage for retry
            this.markMessageFailed(messageId);
            
            // Hide thinking indicator on error
            const thinkingIndicator = document.getElementById('thinkingIndicator');
            if (thinkingIndicator) {
                thinkingIndicator.classList.remove('active');
            }
            
            if (typingIndicator) {
                typingIndicator.classList.remove('active');
            }

            // Show retry UI instead of generic error
            this.showRetryUI(messageId, message);
        } finally {
            sendBtn.disabled = false;
            input.focus();
        }
    },

    scrollToBottom(instant = false) {
        const container = document.getElementById('messagesContainer');
        if (container) {
            // Use requestAnimationFrame to ensure DOM has updated before scrolling
            requestAnimationFrame(() => {
                container.scrollTop = container.scrollHeight;
            });
        }
    },
    
    isNearBottom() {
        // Check if user is scrolled near the bottom (within 100px threshold)
        const container = document.getElementById('messagesContainer');
        if (!container) return true;
        
        const threshold = 100;
        const position = container.scrollTop + container.clientHeight;
        const bottom = container.scrollHeight;
        
        return (bottom - position) < threshold;
    },
    
    scrollToBottomIfNeeded() {
        // Only scroll if user is already near bottom (prevents erratic jumping)
        if (this.isNearBottom()) {
            this.scrollToBottom();
        }
    },

    async renameConversationById(conversationId) {
        const convElement = document.getElementById(`conv-${conversationId}`);
        const currentName = convElement?.querySelector('.conversation-name-sidebar')?.textContent || '';
        
        this.showModal('Rename conversation', currentName, async (name) => {
            if (!name || name.trim() === '') {
                alert('Please enter a conversation name');
                return;
            }

            try {
                const response = await fetch(`/claude/conversations/${conversationId}/rename`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name })
                });

                await response.json();
                await this.loadConversations();
                
                if (this.currentConversation === conversationId) {
                    document.getElementById('topBarTitle').textContent = name;
                }
            } catch (error) {
                console.error('Error renaming conversation:', error);
                alert('Failed to rename conversation');
            }
        });
    },

    async deleteConversationById(conversationId) {
        if (!confirm('Delete this conversation?')) return;

        try {
            await fetch(`/claude/conversations/${conversationId}`, {
                method: 'DELETE'
            });

            await this.loadConversations();
            
            if (this.currentConversation === conversationId) {
                this.currentConversation = null;
                document.getElementById('welcomeScreen').style.display = 'flex';
                document.getElementById('chatArea').style.display = 'none';
                document.getElementById('topBarTitle').textContent = 'InnerVerse - MBTI Master';
            }
        } catch (error) {
            console.error('Error deleting conversation:', error);
            alert('Failed to delete conversation');
        }
    },

    showMoveModalForCurrent() {
        if (this.currentConversation) {
            const convName = document.getElementById('topBarTitle').textContent;
            this.showMoveToProjectModal(this.currentConversation, convName);
        }
    },

    showMoveToProjectModal(conversationId, conversationName) {
        // Create project selection dropdown
        const projectsHtml = this.projects.map(proj => 
            `<button class="project-option" data-project-id="${proj.id}" onclick="app.moveConversationToProject(${conversationId}, '${proj.id}', '${proj.name}')">
                ${proj.emoji} ${proj.name.split(' ').slice(1).join(' ')}
            </button>`
        ).join('');
        
        const modalHtml = `
            <div class="modal active" id="moveModal" onclick="if(event.target.id==='moveModal') app.closeMoveModal()">
                <div class="modal-content" onclick="event.stopPropagation()">
                    <div class="modal-header">Move "${conversationName}" to Project</div>
                    <div class="project-list">
                        ${projectsHtml}
                    </div>
                    <div class="modal-buttons">
                        <button class="modal-btn secondary" onclick="app.closeMoveModal()">Cancel</button>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing move modal if present
        const existing = document.getElementById('moveModal');
        if (existing) existing.remove();
        
        // Add new modal
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    },

    closeMoveModal() {
        const modal = document.getElementById('moveModal');
        if (modal) modal.remove();
    },

    async moveConversationToProject(conversationId, projectId, projectName) {
        try {
            const response = await fetch(`/claude/conversations/${conversationId}/move`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project: projectId })
            });

            if (!response.ok) {
                throw new Error(`Failed to move: ${response.status}`);
            }

            this.closeMoveModal();
            
            // Clear activity cache to force refresh next time Activity is opened
            this.activityCache = null;
            this.activityCacheTime = 0;
            
            // If we're currently viewing a project, reload it to show updated list
            if (this.currentProject) {
                await this.loadConversations();
            }
            
            // If we're currently in Activity tab, refresh the activity view
            if (this.currentTab === 'activity') {
                await this.showActivityView();
            }
            
            // Show success toast
            this.showToast(`Moved to ${projectName.split(' ').slice(1).join(' ')} ✓`);
            
            // If viewing this conversation, navigate to the target project and open it there
            if (this.currentConversation === conversationId) {
                await this.openProject(projectId, projectName);
                setTimeout(() => {
                    this.openConversation(conversationId, document.getElementById('topBarTitle').textContent);
                }, 200);
            }
        } catch (error) {
            console.error('Error moving conversation:', error);
            alert('Failed to move conversation. Please try again.');
        }
    },

    showToast(message) {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 80px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--accent);
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            z-index: 10000;
            animation: slideUp 0.3s ease;
        `;
        
        document.body.appendChild(toast);
        
        // Remove after 3 seconds
        setTimeout(() => {
            toast.style.animation = 'slideDown 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    showModal(title, placeholder, callback) {
        const modal = document.getElementById('nameModal');
        const header = document.getElementById('modalHeader');
        const input = document.getElementById('modalInput');
        
        if (!modal || !header || !input) return;

        header.textContent = title;
        input.placeholder = placeholder;
        input.value = placeholder === input.placeholder ? '' : placeholder;
        this.modalCallback = callback;
        
        modal.classList.add('active');
        setTimeout(() => input.focus(), 100);
    },

    closeModal() {
        const modal = document.getElementById('nameModal');
        const input = document.getElementById('modalInput');
        
        if (modal) modal.classList.remove('active');
        if (input) input.value = '';
        this.modalCallback = null;
    },

    async submitModal() {
        const input = document.getElementById('modalInput');
        if (!input) return;

        const value = input.value.trim();
        if (this.modalCallback) {
            await this.modalCallback(value);
        }
        this.closeModal();
    }
};

document.addEventListener('DOMContentLoaded', () => {
    app.init();
});
