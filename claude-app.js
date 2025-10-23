const app = {
    currentProject: null,
    currentConversation: null,
    projects: [],
    modalCallback: null,
    sidebarOpen: true,

    async init() {
        await this.loadProjects();
        this.renderSidebarProjects();
        this.renderWelcomeCards();
        this.setupEventListeners();
        this.loadSidebarState();
    },

    setupEventListeners() {
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
        
        if (this.sidebarOpen) {
            sidebar.classList.remove('hidden');
        } else {
            sidebar.classList.add('hidden');
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

        container.innerHTML = this.projects.map(project => `
            <div class="project-item" onclick="app.openProject('${project.id}', '${project.name}')">
                <div class="project-emoji">${project.emoji}</div>
                <div class="project-name">${project.name.replace(project.emoji, '').trim()}</div>
            </div>
        `).join('');
    },

    renderWelcomeCards() {
        const container = document.getElementById('welcomeCards');
        if (!container) return;

        container.innerHTML = this.projects.slice(0, 6).map(project => `
            <div class="welcome-card" onclick="app.openProject('${project.id}', '${project.name}')">
                <div class="welcome-card-emoji">${project.emoji}</div>
                <div class="welcome-card-title">${project.name.replace(project.emoji, '').trim()}</div>
            </div>
        `).join('');
    },

    async openProject(projectId, projectName) {
        this.currentProject = projectId;
        
        document.getElementById('topBarTitle').textContent = projectName.split(' ').slice(1).join(' ');
        
        await this.loadConversations();
        
        document.querySelectorAll('.project-item').forEach(item => {
            item.classList.remove('active');
        });
        event.target.closest('.project-item')?.classList.add('active');
        
        if (window.innerWidth <= 768) {
            this.toggleSidebar();
        }
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

    renderSidebarConversations(conversations) {
        const section = document.getElementById('sidebarConversationsSection');
        const container = document.getElementById('sidebarConversations');
        
        if (!container) return;

        section.style.display = 'block';

        if (conversations.length === 0) {
            container.innerHTML = '<div style="padding: 8px; color: var(--text-secondary); font-size: 0.85rem;">No conversations yet</div>';
        } else {
            container.innerHTML = conversations.map(conv => `
                <div class="conversation-item-wrapper ${conv.id === this.currentConversation ? 'active' : ''}" id="conv-${conv.id}">
                    <div class="conversation-name-sidebar" onclick="app.openConversation(${conv.id}, '${conv.name.replace(/'/g, "\\'")}')">${conv.name}</div>
                    <div class="conversation-actions-sidebar">
                        <button class="icon-btn-small" onclick="app.renameConversationById(${conv.id})" title="Rename">✏️</button>
                        <button class="icon-btn-small" onclick="app.deleteConversationById(${conv.id})" title="Delete">🗑️</button>
                    </div>
                </div>
            `).join('');
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

    async openConversation(conversationId, conversationName) {
        this.currentConversation = conversationId;
        
        document.getElementById('topBarTitle').textContent = conversationName;
        
        document.getElementById('welcomeScreen').style.display = 'none';
        document.getElementById('chatArea').style.display = 'flex';

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

    formatMessage(content) {
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

        if (!this.currentConversation) {
            alert('Please select or create a conversation first');
            return;
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
        event.stopPropagation();
        
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
        event.stopPropagation();
        
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
