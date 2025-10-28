// === Phase 3: Sidebar & Organization ===

// State
let conversationId = null;
let isStreaming = false;
let allConversations = [];
let currentMenu = null;

// Folder Configuration
const FOLDERS = [
    { id: 'relationship-lab', name: 'Relationship Lab', icon: '💕' },
    { id: 'mbti-academy', name: 'MBTI Academy', icon: '🎓' },
    { id: 'type-detective', name: 'Type Detective', icon: '🔍' },
    { id: 'trading-psychology', name: 'Trading Psychology', icon: '📈' },
    { id: 'pm-playbook', name: 'PM Playbook', icon: '🎯' },
    { id: 'quick-hits', name: 'Quick Hits', icon: '⚡' },
    { id: 'brain-dump', name: 'Brain Dump', icon: '🧠' }
];

// DOM Elements
const messagesDiv = document.getElementById('messages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const sidebar = document.getElementById('sidebar');
const burgerMenu = document.getElementById('burgerMenu');
const newChatBtn = document.getElementById('newChatBtn');
const sidebarContent = document.getElementById('sidebarContent');
const modalOverlay = document.getElementById('modalOverlay');

// === Sidebar Toggle ===
burgerMenu.addEventListener('click', () => {
    sidebar.classList.toggle('closed');
    burgerMenu.classList.toggle('sidebar-open');
});

// Close sidebar when clicking outside on mobile
document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768) {
        if (!sidebar.contains(e.target) && !burgerMenu.contains(e.target) && !sidebar.classList.contains('closed')) {
            sidebar.classList.add('closed');
            burgerMenu.classList.remove('sidebar-open');
        }
    }
});

// === New Chat Button ===
newChatBtn.addEventListener('click', async () => {
    await createNewConversation('brain-dump');
    // Close sidebar on mobile after creating chat
    if (window.innerWidth <= 768) {
        sidebar.classList.add('closed');
        burgerMenu.classList.remove('sidebar-open');
    }
});

// === Load All Conversations ===
async function loadAllConversations() {
    try {
        const response = await fetch('/claude/conversations/all/list');
        if (!response.ok) throw new Error('Failed to load conversations');
        
        const data = await response.json();
        allConversations = data.conversations || [];
        
        renderSidebar();
        
        // Auto-load most recent conversation
        if (allConversations.length > 0 && !conversationId) {
            const mostRecent = allConversations[0];
            await loadConversation(mostRecent.id);
        } else if (allConversations.length === 0) {
            messagesDiv.innerHTML = '';
        }
    } catch (error) {
        console.error('❌ Error loading conversations:', error);
        sidebarContent.innerHTML = '<div class="error-message">Failed to load conversations</div>';
    }
}

// === Render Sidebar ===
function renderSidebar() {
    // Get folder states from localStorage
    const folderStates = JSON.parse(localStorage.getItem('folderStates') || '{}');
    
    let html = '';
    
    // Render project folders
    FOLDERS.forEach(folder => {
        const conversations = allConversations.filter(c => c.project === folder.id);
        const isExpanded = folderStates[folder.id] === true; // Default: closed
        
        html += `
            <div class="folder ${isExpanded ? 'expanded' : ''}" data-folder="${folder.id}">
                <div class="folder-header" onclick="toggleFolder('${folder.id}')">
                    <span class="folder-arrow">▶</span>
                    <span class="folder-icon">${folder.icon}</span>
                    <span class="folder-name">${folder.name}</span>
                    <span class="folder-count">(${conversations.length})</span>
                </div>
                <div class="folder-conversations">
                    ${conversations.length > 0 
                        ? conversations.map(c => renderConversationItem(c)).join('')
                        : '<div class="empty-folder">No chats yet</div>'
                    }
                </div>
            </div>
        `;
    });
    
    // Add divider and "All Chats" folder
    html += '<div class="folder-divider"></div>';
    
    const allChatsExpanded = folderStates['all-chats'] !== false;
    html += `
        <div class="folder ${allChatsExpanded ? 'expanded' : ''}" data-folder="all-chats">
            <div class="folder-header" onclick="toggleFolder('all-chats')">
                <span class="folder-arrow">▶</span>
                <span class="folder-icon">📋</span>
                <span class="folder-name">All Chats</span>
                <span class="folder-count">(${allConversations.length})</span>
            </div>
            <div class="folder-conversations">
                ${allConversations.length > 0
                    ? allConversations.slice(0, 100).map(c => renderConversationItem(c)).join('')
                    : '<div class="empty-folder">No chats yet</div>'
                }
            </div>
        </div>
    `;
    
    sidebarContent.innerHTML = html;
}

// === Render Conversation Item ===
function renderConversationItem(conv) {
    const title = conv.title || (conv.name && conv.name !== 'New Chat' && conv.name !== 'New Conversation' ? conv.name : 'Untitled Chat');
    const displayTitle = title.length > 40 ? title.substring(0, 40) + '...' : title;
    const isActive = conv.id === conversationId;
    
    return `
        <div class="conversation-item ${isActive ? 'active' : ''}" data-id="${conv.id}" onclick="selectConversation(${conv.id})">
            <span class="conversation-title">${displayTitle}</span>
            <button class="conversation-menu-btn" onclick="event.stopPropagation(); showConversationMenu(${conv.id}, event)">⋮</button>
            <div class="dropdown-menu" id="menu-${conv.id}">
                <div class="dropdown-item" onclick="renameConversation(${conv.id})">Rename</div>
                <div class="dropdown-item" onclick="showMoveConversation(${conv.id})">Move to Folder</div>
                <div class="dropdown-item danger" onclick="deleteConversation(${conv.id})">Delete</div>
            </div>
        </div>
    `;
}

// === Toggle Folder ===
function toggleFolder(folderId) {
    const folderElement = document.querySelector(`[data-folder="${folderId}"]`);
    const isExpanded = folderElement.classList.toggle('expanded');
    
    // Save state to localStorage
    const folderStates = JSON.parse(localStorage.getItem('folderStates') || '{}');
    folderStates[folderId] = isExpanded;
    localStorage.setItem('folderStates', JSON.stringify(folderStates));
}

// === Select Conversation ===
async function selectConversation(id) {
    await loadConversation(id);
    
    // Close sidebar on mobile
    if (window.innerWidth <= 768) {
        sidebar.classList.add('closed');
        burgerMenu.classList.remove('sidebar-open');
    }
}

// === Show Conversation Menu ===
function showConversationMenu(id, event) {
    // Close any open menu
    if (currentMenu) {
        currentMenu.classList.remove('show');
    }
    
    // Open this menu
    const menu = document.getElementById(`menu-${id}`);
    menu.classList.add('show');
    currentMenu = menu;
}

// Close menus when clicking outside
document.addEventListener('click', (e) => {
    if (currentMenu && !e.target.closest('.conversation-menu-btn') && !e.target.closest('.dropdown-menu')) {
        currentMenu.classList.remove('show');
        currentMenu = null;
    }
});

// === Create New Conversation ===
async function createNewConversation(folderId = 'brain-dump') {
    try {
        const folderName = FOLDERS.find(f => f.id === folderId)?.name || 'Brain Dump';
        
        const response = await fetch('/claude/conversations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project: folderId,
                name: 'New Chat'
            })
        });

        if (!response.ok) throw new Error('Failed to create conversation');

        const data = await response.json();
        conversationId = data.id;
        messagesDiv.innerHTML = '';
        console.log('✅ Created new conversation:', conversationId);
        
        // Reload sidebar to show new conversation
        await loadAllConversations();
    } catch (error) {
        console.error('❌ Error creating conversation:', error);
        showError('Failed to create new chat. Please try again.');
    }
}

// === Load Conversation ===
async function loadConversation(id) {
    try {
        const response = await fetch(`/claude/conversations/detail/${id}`);
        if (!response.ok) throw new Error('Failed to load conversation');

        const data = await response.json();
        conversationId = id;
        
        // Clear and display messages
        messagesDiv.innerHTML = '';
        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(msg => {
                addMessage(msg.role, msg.content);
            });
        }
        
        // Update active state in sidebar
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.toggle('active', parseInt(item.dataset.id) === id);
        });
        
        console.log(`✅ Loaded conversation ${id} with ${data.messages?.length || 0} messages`);
    } catch (error) {
        console.error('❌ Error loading conversation:', error);
        messagesDiv.innerHTML = '';
        showError('Failed to load conversation.');
    }
}

// === Rename Conversation ===
function renameConversation(id) {
    if (currentMenu) {
        currentMenu.classList.remove('show');
        currentMenu = null;
    }
    
    const conv = allConversations.find(c => c.id === id);
    const currentTitle = conv?.title || conv?.name || 'Untitled Chat';
    
    showModal({
        title: 'Rename Conversation',
        content: `<input type="text" class="modal-input" id="renameInput" value="${currentTitle}" placeholder="Enter new name">`,
        onShow: () => {
            const input = document.getElementById('renameInput');
            input.focus();
            input.select();
        },
        buttons: [
            { text: 'Cancel', className: 'cancel', onClick: hideModal },
            { text: 'Rename', className: 'confirm', onClick: async () => {
                const newTitle = document.getElementById('renameInput').value.trim();
                if (newTitle) {
                    await updateConversationTitle(id, newTitle);
                    hideModal();
                }
            }}
        ]
    });
}

// === Update Conversation Title ===
async function updateConversationTitle(id, title) {
    try {
        const response = await fetch(`/claude/conversations/${id}/rename`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title })
        });

        if (!response.ok) throw new Error('Failed to rename conversation');

        // Update local state
        const conv = allConversations.find(c => c.id === id);
        if (conv) {
            conv.title = title;
            conv.name = title;
        }
        
        renderSidebar();
        console.log('✅ Renamed conversation:', id);
    } catch (error) {
        console.error('❌ Error renaming conversation:', error);
        showError('Failed to rename conversation.');
    }
}

// === Show Move Conversation Modal ===
function showMoveConversation(id) {
    if (currentMenu) {
        currentMenu.classList.remove('show');
        currentMenu = null;
    }
    
    const conv = allConversations.find(c => c.id === id);
    const currentFolder = conv?.project || 'brain-dump';
    
    const folderOptions = FOLDERS.map(f => 
        `<option value="${f.id}" ${f.id === currentFolder ? 'selected' : ''}>${f.icon} ${f.name}</option>`
    ).join('');
    
    showModal({
        title: 'Move to Folder',
        content: `<select class="modal-select" id="folderSelect">${folderOptions}</select>`,
        buttons: [
            { text: 'Cancel', className: 'cancel', onClick: hideModal },
            { text: 'Move', className: 'confirm', onClick: async () => {
                const newFolder = document.getElementById('folderSelect').value;
                await moveConversation(id, newFolder);
                hideModal();
            }}
        ]
    });
}

// === Move Conversation ===
async function moveConversation(id, folderId) {
    try {
        const response = await fetch(`/claude/conversations/${id}/move`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project: folderId })
        });

        if (!response.ok) throw new Error('Failed to move conversation');

        // Update local state
        const conv = allConversations.find(c => c.id === id);
        if (conv) {
            conv.project = folderId;
        }
        
        renderSidebar();
        console.log('✅ Moved conversation:', id);
    } catch (error) {
        console.error('❌ Error moving conversation:', error);
        showError('Failed to move conversation.');
    }
}

// === Delete Conversation ===
function deleteConversation(id) {
    if (currentMenu) {
        currentMenu.classList.remove('show');
        currentMenu = null;
    }
    
    showModal({
        title: 'Delete Conversation',
        content: '<p>Delete this conversation? This action cannot be undone.</p>',
        buttons: [
            { text: 'Cancel', className: 'cancel', onClick: hideModal },
            { text: 'Delete', className: 'danger', onClick: async () => {
                await performDelete(id);
                hideModal();
            }}
        ]
    });
}

// === Perform Delete ===
async function performDelete(id) {
    try {
        const response = await fetch(`/claude/conversations/${id}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error('Failed to delete conversation');

        // Remove from local state
        allConversations = allConversations.filter(c => c.id !== id);
        
        // If this was the active conversation, clear chat
        if (conversationId === id) {
            conversationId = null;
            messagesDiv.innerHTML = '';
            
            // Load most recent conversation if available
            if (allConversations.length > 0) {
                await loadConversation(allConversations[0].id);
            }
        }
        
        renderSidebar();
        console.log('✅ Deleted conversation:', id);
    } catch (error) {
        console.error('❌ Error deleting conversation:', error);
        showError('Failed to delete conversation.');
    }
}

// === Modal Functions ===
function showModal({ title, content, buttons, onShow }) {
    const modalHTML = `
        <div class="modal">
            <div class="modal-title">${title}</div>
            <div class="modal-content">${content}</div>
            <div class="modal-buttons">
                ${buttons.map((btn, i) => 
                    `<button class="modal-btn ${btn.className}" data-btn-index="${i}">${btn.text}</button>`
                ).join('')}
            </div>
        </div>
    `;
    
    modalOverlay.innerHTML = modalHTML;
    modalOverlay.classList.add('show');
    
    // Attach button handlers
    buttons.forEach((btn, i) => {
        const btnElement = modalOverlay.querySelector(`[data-btn-index="${i}"]`);
        btnElement.addEventListener('click', btn.onClick);
    });
    
    if (onShow) {
        setTimeout(onShow, 10);
    }
}

function hideModal() {
    modalOverlay.classList.remove('show');
    modalOverlay.innerHTML = '';
}

// === Message Functions ===
function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? 'U' : 'A';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    messagesDiv.appendChild(messageDiv);

    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    return contentDiv;
}

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    messagesDiv.appendChild(errorDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// === Send Message ===
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message || isStreaming || !conversationId) return;

    messageInput.value = '';
    isStreaming = true;
    sendButton.disabled = true;

    addMessage('user', message);

    const assistantContent = addMessage('assistant', '');
    let fullResponse = '';

    try {
        const response = await fetch(`/claude/conversations/${conversationId}/message/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });

        if (!response.ok) throw new Error('Failed to send message');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        
                        if (data.chunk) {
                            fullResponse += data.chunk;
                            assistantContent.textContent = fullResponse;
                            messagesDiv.scrollTop = messagesDiv.scrollHeight;
                        }

                        if (data.error) {
                            showError(data.error);
                        }
                    } catch (e) {
                        console.error('Error parsing SSE:', e);
                    }
                }
            }
        }
        
        // Reload sidebar to update conversation timestamp
        await loadAllConversations();
    } catch (error) {
        console.error('❌ Error sending message:', error);
        showError('Failed to get response. Please try again.');
    } finally {
        isStreaming = false;
        sendButton.disabled = false;
        messageInput.focus();
    }
}

// === Event Listeners ===
sendButton.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// === Initialize ===
// Check if sidebar should be closed on mobile by default
if (window.innerWidth <= 768) {
    sidebar.classList.add('closed');
}

// Load conversations on startup
loadAllConversations();
