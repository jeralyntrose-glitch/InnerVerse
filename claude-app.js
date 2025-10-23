const app = {
    currentProject: null,
    currentConversation: null,
    projects: [],
    modalCallback: null,

    async init() {
        await this.loadProjects();
        this.renderProjects();
        this.setupEventListeners();
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

        const globalSearch = document.getElementById('globalSearch');
        if (globalSearch) {
            let searchTimeout;
            globalSearch.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.searchGlobal(e.target.value);
                }, 300);
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

    renderProjects() {
        const grid = document.getElementById('projectGrid');
        if (!grid) return;

        grid.innerHTML = this.projects.map(project => `
            <div class="project-card" onclick="app.openProject('${project.id}', '${project.name}')">
                <div class="emoji">${project.emoji}</div>
                <h3>${project.name.replace(project.emoji, '').trim()}</h3>
                <p>${project.description}</p>
            </div>
        `).join('');
    },

    async openProject(projectId, projectName) {
        this.currentProject = projectId;
        document.getElementById('projectTitle').textContent = projectName;
        await this.loadConversations();
        this.showView('conversationsView');
    },

    async loadConversations() {
        try {
            const response = await fetch(`/claude/conversations/${this.currentProject}`);
            const data = await response.json();
            this.renderConversations(data.conversations);
        } catch (error) {
            console.error('Error loading conversations:', error);
            this.renderConversations([]);
        }
    },

    renderConversations(conversations) {
        const list = document.getElementById('conversationList');
        if (!list) return;

        if (conversations.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">💬</div>
                    <p>No conversations yet. Start a new one!</p>
                </div>
            `;
            return;
        }

        list.innerHTML = conversations.map(conv => {
            const date = new Date(conv.updated_at);
            const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            
            return `
                <div class="conversation-item" onclick="app.openConversation(${conv.id}, '${conv.name.replace(/'/g, "\\'")}')">
                    <div>
                        <div class="conversation-name">${conv.name}</div>
                        <div class="conversation-date">${dateStr}</div>
                    </div>
                </div>
            `;
        }).join('');
    },

    async createNewConversation() {
        this.showModal('Name your conversation', 'e.g., ENFP-INFJ Golden Pair', async (name) => {
            if (!name || name.trim() === '') {
                alert('Please enter a conversation name');
                return;
            }

            try {
                const response = await fetch('/claude/conversations', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        project: this.currentProject,
                        name: name
                    })
                });

                const conversation = await response.json();
                this.openConversation(conversation.id, conversation.name);
            } catch (error) {
                console.error('Error creating conversation:', error);
                alert('Failed to create conversation');
            }
        });
    },

    async openConversation(convId, convName) {
        this.currentConversation = convId;
        document.getElementById('chatTitle').textContent = convName;
        
        try {
            const response = await fetch(`/claude/conversations/detail/${convId}`);
            const data = await response.json();
            this.renderMessages(data.messages);
            this.showView('chatView');
            
            setTimeout(() => {
                const input = document.getElementById('messageInput');
                if (input) input.focus();
            }, 100);
        } catch (error) {
            console.error('Error loading conversation:', error);
            alert('Failed to load conversation');
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

        // Scroll instantly to bottom when loading conversation
        // Use requestAnimationFrame to ensure DOM is fully rendered first
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                this.scrollToBottom(true);
            });
        });
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
                // When loading conversations, scroll instantly to bottom
                container.scrollTop = container.scrollHeight;
            } else {
                // When sending new messages, scroll smoothly with offset to keep visible
                const messages = container.querySelectorAll('.message');
                if (messages.length > 0) {
                    const lastMessage = messages[messages.length - 1];
                    lastMessage.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'end',
                        inline: 'nearest' 
                    });
                    
                    setTimeout(() => {
                        // Offset by 100px to keep message comfortably visible
                        container.scrollTop = container.scrollTop - 100;
                    }, 100);
                } else {
                    container.scrollTop = container.scrollHeight;
                }
            }
        }
    },

    async renameConversation() {
        const currentName = document.getElementById('chatTitle').textContent;
        this.showModal('Rename conversation', currentName, async (name) => {
            if (!name || name.trim() === '') {
                alert('Please enter a conversation name');
                return;
            }

            try {
                const response = await fetch(`/claude/conversations/${this.currentConversation}/rename`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name })
                });

                const data = await response.json();
                document.getElementById('chatTitle').textContent = data.name;
            } catch (error) {
                console.error('Error renaming conversation:', error);
                alert('Failed to rename conversation');
            }
        });
    },

    async deleteConversation() {
        if (!confirm('Are you sure you want to delete this conversation? This cannot be undone.')) {
            return;
        }

        try {
            await fetch(`/claude/conversations/${this.currentConversation}`, {
                method: 'DELETE'
            });

            this.showConversations();
        } catch (error) {
            console.error('Error deleting conversation:', error);
            alert('Failed to delete conversation');
        }
    },

    async searchGlobal(query) {
        if (!query || query.trim() === '') {
            this.renderProjects();
            return;
        }

        try {
            const response = await fetch(`/claude/search?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            const grid = document.getElementById('projectGrid');
            if (!grid) return;

            if (data.results.length === 0) {
                grid.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">🔍</div>
                        <p>No results found for "${query}"</p>
                    </div>
                `;
                return;
            }

            grid.innerHTML = data.results.map(result => {
                const project = this.projects.find(p => p.id === result.project);
                const date = new Date(result.updated_at);
                const dateStr = date.toLocaleDateString();
                
                return `
                    <div class="project-card" onclick="app.openConversation(${result.id}, '${result.name.replace(/'/g, "\\'")}')">
                        <div class="emoji">${project ? project.emoji : '💬'}</div>
                        <h3>${result.name}</h3>
                        <p>${result.preview ? result.preview.substring(0, 100) + '...' : ''}</p>
                        <p style="font-size: 0.85rem; color: #6B7280; margin-top: 8px;">${dateStr}</p>
                    </div>
                `;
            }).join('');
        } catch (error) {
            console.error('Error searching:', error);
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
    },

    showView(viewId) {
        document.querySelectorAll('.view').forEach(view => {
            view.classList.remove('active');
        });
        
        const view = document.getElementById(viewId);
        if (view) view.classList.add('active');
    },

    showHome() {
        this.currentProject = null;
        this.currentConversation = null;
        this.showView('homeView');
        this.renderProjects();
        document.getElementById('globalSearch').value = '';
    },

    async showConversations() {
        this.currentConversation = null;
        await this.loadConversations();
        this.showView('conversationsView');
    }
};

document.addEventListener('DOMContentLoaded', () => {
    app.init();
});
