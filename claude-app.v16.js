const app = {
    currentProject: null,
    currentConversation: null,
    projects: [],
    modalCallback: null,
    sidebarOpen: true,
    currentTab: 'home',
    isMobile: false,

    async init() {
        this.detectMobile();
        await this.loadProjects();
        this.renderSidebarProjects();
        this.showDefaultChatView();
        this.setupEventListeners();
        this.loadSidebarState();
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
        
        // Update tab buttons
        document.querySelectorAll('.sidebar-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.getElementById(`tab${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`).classList.add('active');
        
        // Update tab content
        document.querySelectorAll('.sidebar-tab-content').forEach(content => {
            content.classList.add('hidden');
        });
        document.getElementById(`tabContent${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`).classList.remove('hidden');
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
            messageInput.style.height = messageInput.scrollHeight + 'px';
            
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

            messageInput.addEventListener('input', () => {
                messageInput.style.height = 'auto';
                messageInput.style.height = messageInput.scrollHeight + 'px';
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
        
        document.getElementById('topBarTitle').textContent = projectName.split(' ').slice(1).join(' ');
        
        await this.loadConversations();
        this.renderProjectChatView();
        
        this.updateActiveProject();
        
        if (window.innerWidth <= 768) {
            this.toggleSidebar();
        }
    },

    renderProjectChatView() {
        // When opening a project without selecting a conversation, show welcome screen
        const welcomeScreen = document.getElementById('welcomeScreen');
        const messagesContainer = document.getElementById('messagesContainer');
        
        if (welcomeScreen) {
            welcomeScreen.classList.remove('hidden');
        }
        if (messagesContainer) {
            messagesContainer.classList.add('hidden');
            messagesContainer.innerHTML = '';
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
                wrapper.className = 'conversation-item-wrapper';
                wrapper.id = `conv-${conv.id}`;
                if (conv.id === this.currentConversation) {
                    wrapper.classList.add('active');
                }

                const nameDiv = document.createElement('div');
                nameDiv.className = 'conversation-name-sidebar';
                nameDiv.textContent = conv.name || 'New Chat';
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
            if (messagesContainer) messagesContainer.classList.remove('hidden');
            if (inputSuggestions) inputSuggestions.classList.add('hidden');
            
            return true;
        } catch (error) {
            console.error('Error auto-creating conversation:', error);
            return false;
        }
    },

    async openConversation(conversationId, conversationName) {
        this.currentConversation = conversationId;
        
        // Show move button when conversation is open
        const moveBtn = document.getElementById('move-to-project-btn');
        if (moveBtn) moveBtn.style.display = 'flex';
        
        // Display conversation name with project badge if applicable
        const currentProjectObj = this.projects.find(p => p.id === this.currentProject);
        const projectPrefix = currentProjectObj ? `${currentProjectObj.emoji} ` : '';
        document.getElementById('topBarTitle').textContent = `${projectPrefix}${conversationName}`;
        
        // Hide welcome screen, show messages container
        const welcomeScreen = document.getElementById('welcomeScreen');
        const messagesContainer = document.getElementById('messagesContainer');
        
        if (welcomeScreen) {
            welcomeScreen.classList.add('hidden');
        }
        if (messagesContainer) {
            messagesContainer.classList.remove('hidden');
        }

        document.querySelectorAll('.conversation-item-wrapper').forEach(item => {
            item.classList.remove('active');
        });
        document.getElementById(`conv-${conversationId}`)?.classList.add('active');

        try {
            const response = await fetch(`/claude/conversations/detail/${conversationId}`);
            const data = await response.json();
            this.renderMessages(data.messages);
        } catch (error) {
            console.error('Error loading conversation:', error);
        }

        if (window.innerWidth <= 768) {
            this.toggleSidebar();
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

        input.value = '';
        input.style.height = 'auto';
        sendBtn.disabled = true;

        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'message user';
        userMessageDiv.textContent = message;
        
        const container = document.getElementById('messagesContainer');
        container.insertBefore(userMessageDiv, typingIndicator);
        this.scrollToBottom();

        if (typingIndicator) {
            typingIndicator.classList.add('active');
        }

        try {
            const response = await fetch(`/claude/conversations/${this.currentConversation}/message`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });

            const data = await response.json();

            if (typingIndicator) {
                typingIndicator.classList.remove('active');
            }

            const assistantMessageDiv = document.createElement('div');
            assistantMessageDiv.className = 'message assistant';
            assistantMessageDiv.innerHTML = this.formatMessage(data.assistant_message.content);
            container.insertBefore(assistantMessageDiv, typingIndicator);
            
            this.scrollToBottom();
        } catch (error) {
            console.error('Error sending message:', error);
            
            if (typingIndicator) {
                typingIndicator.classList.remove('active');
            }

            const errorDiv = document.createElement('div');
            errorDiv.className = 'message assistant';
            errorDiv.textContent = 'Sorry, I encountered an error. Please try again.';
            container.insertBefore(errorDiv, typingIndicator);
        } finally {
            sendBtn.disabled = false;
            input.focus();
        }
    },

    scrollToBottom(instant = false) {
        const container = document.getElementById('messagesContainer');
        if (container) {
            if (instant) {
                container.scrollTop = container.scrollHeight;
            } else {
                const messages = container.querySelectorAll('.message');
                if (messages.length > 0) {
                    const lastMessage = messages[messages.length - 1];
                    lastMessage.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'end',
                        inline: 'nearest' 
                    });
                    
                    setTimeout(() => {
                        container.scrollTop = container.scrollTop - 100;
                    }, 100);
                } else {
                    container.scrollTop = container.scrollHeight;
                }
            }
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
            await fetch(`/claude/conversations/${conversationId}/move`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project: projectId })
            });

            this.closeMoveModal();
            await this.loadConversations();
            
            // Show success toast
            this.showToast(`Moved to ${projectName.split(' ').slice(1).join(' ')} ✓`);
            
            // If viewing this conversation, update top bar
            if (this.currentConversation === conversationId) {
                // Update project context
                this.currentProject = projectId;
                document.getElementById('topBarTitle').textContent = projectName.split(' ').slice(1).join(' ');
            }
        } catch (error) {
            console.error('Error moving conversation:', error);
            alert('Failed to move conversation');
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
