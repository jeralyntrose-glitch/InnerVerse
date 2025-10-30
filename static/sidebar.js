// === Phase 3: Sidebar & Organization ===
// === Phase 5: Search & Copy Utility Features ===

console.log('🟢🟢🟢 SIDEBAR.JS IS LOADING! 🟢🟢🟢');

// State
let conversationId = null;
let isStreaming = false;
let allConversations = [];
let currentMenu = null;
let searchTerm = '';
let searchDebounceTimer = null;
let isBackendSearch = false; // Flag to track if we're using backend search results

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
// Removed: old typing indicator constant
const searchInput = document.getElementById('searchInput');
const searchClearBtn = document.getElementById('searchClearBtn');
const uploadButton = document.getElementById('uploadButton');
const imageUpload = document.getElementById('imageUpload');
const uploadError = document.getElementById('uploadError');
const imagePreviewContainer = document.getElementById('imagePreviewContainer');

// Initialize sidebar state on mobile
if (window.innerWidth <= 768) {
    sidebar.classList.add('closed');
}

// === Auto-expand textarea ===
function autoExpandTextarea() {
    messageInput.style.height = 'auto'; // Reset height
    messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + 'px'; // Expand to content, max 150px
}

// Add auto-expand on input
messageInput.addEventListener('input', autoExpandTextarea);

// === Phase 6: Image Upload ===
let selectedImage = null;

// File validation constants
const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB in bytes
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];

// Show error message
function showUploadError(message) {
    uploadError.textContent = message;
    uploadError.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        uploadError.style.display = 'none';
    }, 5000);
}

// Format file size for display
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// Validate image file
function validateImage(file) {
    if (!file) {
        showUploadError('No file selected');
        return false;
    }
    
    // Check file type
    if (!ALLOWED_TYPES.includes(file.type) && !file.type.startsWith('image/')) {
        showUploadError('Please upload an image file (JPEG, PNG, GIF, or WebP)');
        return false;
    }
    
    // Check file size
    if (file.size > MAX_FILE_SIZE) {
        const fileSize = formatFileSize(file.size);
        showUploadError(`Image must be under 5MB. Your file is ${fileSize}`);
        return false;
    }
    
    return true;
}

// Upload button click handler
uploadButton.addEventListener('click', () => {
    imageUpload.click();
});

// Show image preview
function showImagePreview(file, dataUrl) {
    const fileName = file.name.length > 40 ? file.name.substring(0, 37) + '...' : file.name;
    const fileSize = formatFileSize(file.size);
    
    imagePreviewContainer.innerHTML = `
        <div class="image-preview">
            <img src="${dataUrl}" alt="Preview" class="image-preview-thumbnail">
            <div class="image-preview-info">
                <div class="image-preview-filename">${fileName}</div>
                <div class="image-preview-filesize">${fileSize}</div>
            </div>
            <button class="image-preview-remove" id="removeImageBtn" type="button">×</button>
        </div>
    `;
    
    imagePreviewContainer.style.display = 'block';
    
    // Update placeholder
    messageInput.placeholder = 'Add a message (optional)...';
    
    // Add event listener for remove button
    document.getElementById('removeImageBtn').addEventListener('click', clearImagePreview);
}

// Clear image preview
function clearImagePreview() {
    selectedImage = null;
    imagePreviewContainer.innerHTML = '';
    imagePreviewContainer.style.display = 'none';
    imageUpload.value = '';
    uploadButton.classList.remove('file-selected');
    messageInput.placeholder = 'Type your message...';
}

// File input change handler
imageUpload.addEventListener('change', (e) => {
    const file = e.target.files[0];
    
    if (!file) {
        return;
    }
    
    // Validate file
    if (!validateImage(file)) {
        imageUpload.value = ''; // Clear the input
        return;
    }
    
    // File is valid - read it and show preview
    const reader = new FileReader();
    reader.onload = (e) => {
        selectedImage = file;
        uploadButton.classList.add('file-selected');
        showImagePreview(file, e.target.result);
        console.log('Image selected:', file.name, formatFileSize(file.size));
    };
    reader.readAsDataURL(file);
});

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

// === Phase 5: Search Functionality ===
// Search input event listener with debounce (300ms)
searchInput.addEventListener('input', (e) => {
    const value = e.target.value.trim();
    
    // Show/hide clear button
    searchClearBtn.style.display = value ? 'flex' : 'none';
    
    // Debounce search (wait 300ms after user stops typing)
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(async () => {
        searchTerm = value;
        await performSearch();
    }, 300);
});

// Clear button click listener
searchClearBtn.addEventListener('click', async () => {
    searchInput.value = '';
    searchTerm = '';
    isBackendSearch = false;
    searchClearBtn.style.display = 'none';
    await loadAllConversations(); // Reload all conversations
    searchInput.focus(); // Keep focus for better UX
});

// ESC key to clear search
searchInput.addEventListener('keydown', async (e) => {
    if (e.key === 'Escape') {
        searchInput.value = '';
        searchTerm = '';
        isBackendSearch = false;
        searchClearBtn.style.display = 'none';
        await loadAllConversations(); // Reload all conversations
    }
});

// === Phase 5: Backend Search Function ===
async function performSearch() {
    if (!searchTerm) {
        // If search is empty, reload all conversations
        isBackendSearch = false;
        await loadAllConversations();
        return;
    }
    
    try {
        console.log('🔍 Searching for:', searchTerm);
        // Call backend search endpoint (searches titles AND message content)
        const response = await fetch(`/claude/conversations/search?q=${encodeURIComponent(searchTerm)}`);
        console.log('📡 Search response status:', response.status);
        if (!response.ok) throw new Error('Search failed');
        
        const data = await response.json();
        console.log('📦 Search results:', data.conversations?.length, 'conversations');
        allConversations = data.conversations || [];
        isBackendSearch = true; // Mark as backend search results
        
        renderSidebar();
    } catch (error) {
        console.error('❌ Error searching conversations:', error);
        // Fall back to client-side title-only search
        isBackendSearch = false;
        renderSidebar();
    }
}

// === Search Filter Function (Client-Side Fallback) ===
function filterConversations(conversations) {
    if (!searchTerm) return conversations;
    
    const term = searchTerm.toLowerCase();
    
    return conversations.filter(conv => {
        const title = (conv.title || conv.name || '').toLowerCase();
        
        // Search in conversation title (fallback if backend search fails)
        return title.includes(term);
    });
}

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
    // Get folder states from localStorage (only used when NOT searching)
    const folderStates = JSON.parse(localStorage.getItem('folderStates') || '{}');
    
    let html = '';
    
    // IMPORTANT: If using backend search results, DON'T filter again!
    // Backend already returned filtered results (titles + message content)
    // Only apply client-side filtering if NOT using backend search
    const filteredConversations = isBackendSearch ? allConversations : filterConversations(allConversations);
    
    // === Phase 5: Flat Search Results (No Folder Organization) ===
    if (searchTerm) {
        // Show flat list of search results (no folders)
        if (filteredConversations.length === 0) {
            html = `
                <div class="search-empty-state">
                    <strong>No conversations found matching "${escapeHTML(searchTerm)}"</strong>
                    Try a different search term
                </div>
            `;
        } else {
            html = `
                <div class="search-results-header">
                    <strong>Search Results</strong>
                    <span class="folder-count">(${filteredConversations.length})</span>
                </div>
                <div class="search-results-list">
                    ${filteredConversations.slice(0, 100).map(c => renderConversationItem(c)).join('')}
                </div>
            `;
        }
        
        sidebarContent.innerHTML = html;
        return;
    }
    
    // === Normal Mode: Show Folders ===
    // Render project folders
    FOLDERS.forEach(folder => {
        const folderConvs = allConversations.filter(c => c.project === folder.id);
        const isExpanded = folderStates[folder.id] === true;
        
        html += `
            <div class="folder ${isExpanded ? 'expanded' : ''}" data-folder="${folder.id}">
                <div class="folder-header" onclick="toggleFolder('${folder.id}')">
                    <span class="folder-arrow">▶</span>
                    <span class="folder-icon">${folder.icon}</span>
                    <span class="folder-name">${folder.name}</span>
                    <span class="folder-count">(${folderConvs.length})</span>
                </div>
                <div class="folder-conversations">
                    ${folderConvs.length > 0 
                        ? folderConvs.map(c => renderConversationItem(c)).join('')
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

// SECURITY: Escape HTML to prevent XSS in sidebar
function escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// === Render Conversation Item ===
function renderConversationItem(conv) {
    const title = conv.title || (conv.name && conv.name !== 'New Chat' && conv.name !== 'New Conversation' ? conv.name : 'Untitled Chat');
    const displayTitle = title.length > 40 ? title.substring(0, 40) + '...' : title;
    const isActive = conv.id === conversationId;
    
    // SECURITY: Escape user-controlled title to prevent XSS
    const safeTitle = escapeHTML(displayTitle);
    
    return `
        <div class="conversation-item ${isActive ? 'active' : ''}" data-id="${conv.id}" onclick="selectConversation(${conv.id})">
            <span class="conversation-title">${safeTitle}</span>
            <button class="conversation-menu-btn" onclick="event.stopPropagation(); showConversationMenu(${conv.id}, event)">⋮</button>
            <div class="dropdown-menu" id="menu-${conv.id}">
                <div class="dropdown-item" onclick="event.stopPropagation(); renameConversation(${conv.id})">Rename</div>
                <div class="dropdown-item" onclick="event.stopPropagation(); showMoveConversation(${conv.id})">Move to Folder</div>
                <div class="dropdown-item danger" onclick="event.stopPropagation(); deleteConversation(${conv.id})">Delete</div>
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
    
    // Find the menu relative to the button that was clicked
    // This ensures we get the correct menu even with duplicate IDs
    const button = event.target;
    const conversationItem = button.closest('.conversation-item');
    const menu = conversationItem.querySelector('.dropdown-menu');
    
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
                addMessage(msg.role, msg.content, null, msg.follow_up_question);
            });
            
            // Scroll to bottom after loading all messages
            setTimeout(() => {
                scrollToBottom();
            }, 100);
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
        // SECURITY: Don't inject user data into attributes - set via DOM instead
        content: `<input type="text" class="modal-input" id="renameInput" placeholder="Enter new name">`,
        onShow: () => {
            const input = document.getElementById('renameInput');
            // SECURITY: Set value via DOM API to prevent XSS
            input.value = currentTitle;
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
            body: JSON.stringify({ name: title })
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
// Helper: Only auto-scroll if user is already near the bottom
function shouldAutoScroll() {
    const threshold = 100; // pixels from bottom
    const distanceFromBottom = messagesDiv.scrollHeight - messagesDiv.scrollTop - messagesDiv.clientHeight;
    return distanceFromBottom < threshold;
}

function scrollToBottom() {
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// === Phase 5 Part 2: Copy Message Functionality ===

// Strip markdown from AI messages to get plain text
function stripMarkdown(text) {
    let plain = text;
    
    // Remove code blocks
    plain = plain.replace(/```[\s\S]*?```/g, (match) => {
        // Extract code content, preserve formatting
        return match.replace(/```\w*\n?/g, '').replace(/```$/g, '');
    });
    
    // Remove inline code
    plain = plain.replace(/`([^`]+)`/g, '$1');
    
    // Remove bold
    plain = plain.replace(/\*\*([^*]+)\*\*/g, '$1');
    plain = plain.replace(/__([^_]+)__/g, '$1');
    
    // Remove italic
    plain = plain.replace(/\*([^*]+)\*/g, '$1');
    plain = plain.replace(/_([^_]+)_/g, '$1');
    
    // Remove headers
    plain = plain.replace(/^#{1,6}\s+(.+)$/gm, '$1');
    
    // Remove strikethrough
    plain = plain.replace(/~~([^~]+)~~/g, '$1');
    
    // Remove blockquotes
    plain = plain.replace(/^>\s+(.+)$/gm, '$1');
    
    // Remove horizontal rules
    plain = plain.replace(/^([-*_]){3,}$/gm, '');
    
    // Remove list markers (preserve content)
    plain = plain.replace(/^[\s]*[-*+]\s+(.+)$/gm, '$1');
    plain = plain.replace(/^[\s]*\d+\.\s+(.+)$/gm, '$1');
    
    // Remove links but keep text
    plain = plain.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
    
    // Remove images
    plain = plain.replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1');
    
    // Clean up extra whitespace but preserve structure
    plain = plain.replace(/\n{3,}/g, '\n\n');
    plain = plain.trim();
    
    return plain;
}

// Copy message to clipboard with fallback
async function copyMessageToClipboard(messageText, isAIMessage, button) {
    console.log('📋 copyMessageToClipboard called', { isAIMessage, textLength: messageText.length });
    
    try {
        // Strip markdown if AI message
        const plainText = isAIMessage ? stripMarkdown(messageText) : messageText;
        console.log('📋 Plain text prepared:', plainText.substring(0, 100));
        
        // Try modern Clipboard API
        if (navigator.clipboard && navigator.clipboard.writeText) {
            console.log('📋 Using modern Clipboard API');
            await navigator.clipboard.writeText(plainText);
            console.log('✅ Copy successful!');
            showCopySuccess(button);
        } else {
            console.log('📋 Using fallback copy method');
            // Fallback for older browsers
            fallbackCopy(plainText, button);
        }
    } catch (err) {
        console.error('❌ Clipboard error:', err);
        // Try fallback method
        const plainText = isAIMessage ? stripMarkdown(messageText) : messageText;
        fallbackCopy(plainText, button);
    }
}

// Fallback copy method for older browsers
function fallbackCopy(text, button) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    
    try {
        textarea.select();
        textarea.setSelectionRange(0, textarea.value.length);
        const success = document.execCommand('copy');
        
        if (success) {
            showCopySuccess(button);
        } else {
            showCopyError(button);
        }
    } catch (err) {
        console.error('Fallback copy failed:', err);
        showCopyError(button);
    } finally {
        document.body.removeChild(textarea);
    }
}

// Show copy success feedback
function showCopySuccess(button) {
    console.log('✅ Showing copy success feedback');
    button.classList.add('copied');
    button.setAttribute('data-tooltip', 'Copied!');
    
    // Change icon to checkmark
    button.innerHTML = `
        <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M13.5 4L6 11.5L2.5 8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
    `;
    
    // Reset after 2 seconds
    setTimeout(() => {
        button.classList.remove('copied');
        button.setAttribute('data-tooltip', 'Copy message');
        button.innerHTML = `
            <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="5.5" y="5.5" width="8" height="8" rx="1.5" stroke="#A0A0A0" stroke-width="1.2" fill="none"/>
                <path d="M3.5 10.5V3.5C3.5 2.67 4.17 2 5 2H10.5" stroke="#A0A0A0" stroke-width="1.2" stroke-linecap="round" fill="none"/>
            </svg>
        `;
    }, 2000);
}

// Show copy error feedback
function showCopyError(button) {
    button.setAttribute('data-tooltip', 'Copy failed');
    
    // Reset after 2 seconds
    setTimeout(() => {
        button.setAttribute('data-tooltip', 'Copy message');
    }, 2000);
}

// Professional Phase 4 & 6 & 9: Markdown-enabled message rendering with image support and follow-up questions
function addMessage(role, content, imageFile = null, followUpQuestion = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // === Phase 9: Strip [FOLLOW-UP: ...] brackets from AI message content ===
    if (role === 'assistant' && content) {
        content = content.replace(/\[FOLLOW-UP:\s*/g, '').replace(/\]/g, '');
    }
    
    // === Phase 6: Add image if provided (for user messages) ===
    if (imageFile && role === 'user') {
        const reader = new FileReader();
        reader.onload = (e) => {
            const imgElement = document.createElement('img');
            imgElement.src = e.target.result;
            imgElement.className = 'message-image';
            imgElement.style.cssText = 'max-width: 300px; width: 100%; height: auto; border-radius: 12px; margin-bottom: 8px; display: block;';
            contentDiv.insertBefore(imgElement, contentDiv.firstChild);
        };
        reader.readAsDataURL(imageFile);
    }
    
    // Render markdown for AI messages, plain text for user messages
    if (role === 'assistant' && typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
        // Configure marked for security
        marked.setOptions({
            breaks: true,
            gfm: true,
            headerIds: false,
            mangle: false
        });
        
        // SECURITY: Sanitize markdown output before injecting into DOM
        const rawHTML = marked.parse(content);
        const cleanHTML = DOMPurify.sanitize(rawHTML, {
            ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                          'ul', 'ol', 'li', 'code', 'pre', 'blockquote', 'a', 'hr'],
            ALLOWED_ATTR: ['href', 'target', 'rel', 'class']
        });
        contentDiv.innerHTML = cleanHTML;
        
        // Make links open in new tab
        contentDiv.querySelectorAll('a').forEach(link => {
            link.setAttribute('target', '_blank');
            link.setAttribute('rel', 'noopener noreferrer');
        });
    } else if (content) {
        // Add text content if provided
        const textSpan = document.createElement('span');
        textSpan.textContent = content;
        contentDiv.appendChild(textSpan);
    }

    messageDiv.appendChild(contentDiv);
    
    // === Phase 5 Part 2: Add Copy Button ===
    const copyButton = document.createElement('button');
    copyButton.className = 'copy-btn';
    copyButton.setAttribute('data-tooltip', 'Copy message');
    copyButton.setAttribute('aria-label', 'Copy message');
    copyButton.setAttribute('tabindex', '0');
    copyButton.innerHTML = `
        <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="5.5" y="5.5" width="8" height="8" rx="1.5" stroke="#A0A0A0" stroke-width="1.2" fill="none"/>
            <path d="M3.5 10.5V3.5C3.5 2.67 4.17 2 5 2H10.5" stroke="#A0A0A0" stroke-width="1.2" stroke-linecap="round" fill="none"/>
        </svg>
    `;
    
    // Add click handler
    copyButton.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent any parent click handlers
        e.preventDefault(); // Prevent default action
        console.log('📋 Copy button clicked!', { content: content.substring(0, 50), role });
        copyMessageToClipboard(content, role === 'assistant', copyButton);
    });
    
    // Add keyboard support (Enter and Space)
    copyButton.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            copyMessageToClipboard(content, role === 'assistant', copyButton);
        }
    });
    
    messageDiv.appendChild(copyButton);
    messagesDiv.appendChild(messageDiv);

    // Only auto-scroll if user is already at bottom
    if (shouldAutoScroll()) {
        scrollToBottom();
    }

    return contentDiv;
}

// === SIMPLE TYPING INDICATOR ===
function showTyping() {
    console.log('🔵 SHOWING typing indicator');
    const typing = document.getElementById('ai-typing');
    if (typing) {
        typing.style.display = 'block';
        setTimeout(() => scrollToBottom(), 50);
    } else {
        console.error('❌ ai-typing element not found!');
    }
}

function hideTyping() {
    console.log('🔴 HIDING typing indicator');
    const typing = document.getElementById('ai-typing');
    if (typing) {
        typing.style.display = 'none';
    }
}

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    messagesDiv.appendChild(errorDiv);
    // Only auto-scroll if user is already at bottom
    if (shouldAutoScroll()) {
        scrollToBottom();
    }
}

// === Send Message ===
async function sendMessage() {
    console.log('🚀 sendMessage CALLED');
    
    const message = messageInput.value.trim();
    const hasImage = selectedImage !== null;
    
    console.log('📝 Message:', message, '| hasImage:', hasImage, '| isStreaming:', isStreaming, '| conversationId:', conversationId);
    
    // Allow sending if there's a message OR an image
    if ((!message && !hasImage) || isStreaming || !conversationId) {
        console.log('❌ Blocked from sending - conditions not met');
        return;
    }

    messageInput.value = '';
    messageInput.style.height = 'auto'; // Reset textarea height
    isStreaming = true;
    sendButton.disabled = true;

    // Prepare message payload
    let messagePayload = { message: message || '' };
    
    // If there's an image, convert to base64 and add to payload
    if (hasImage) {
        const reader = new FileReader();
        const imageDataPromise = new Promise((resolve, reject) => {
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(selectedImage);
        });
        
        try {
            const imageDataUrl = await imageDataPromise;
            // Backend expects image data as a base64 string
            messagePayload.image = imageDataUrl;
        } catch (error) {
            console.error('Error reading image:', error);
            showError('Failed to process image. Please try again.');
            isStreaming = false;
            sendButton.disabled = false;
            return;
        }
    }

    // Display user message (with or without image)
    addMessage('user', message, hasImage ? selectedImage : null);
    
    // Force scroll to show user message
    scrollToBottom();
    
    // Clear image preview after adding to chat
    if (hasImage) {
        clearImagePreview();
    }
    
    // Show typing indicator
    showTyping();
    
    // Force scroll to show typing indicator
    setTimeout(() => scrollToBottom(), 100);

    let assistantContent = null;
    let fullResponse = '';

    try {
        const response = await fetch(`/claude/conversations/${conversationId}/message/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(messagePayload)
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
                            // On first chunk, hide typing indicator and create assistant message
                            if (!assistantContent) {
                                console.log('📥 First chunk received, creating assistant message');
                                hideTyping();
                                assistantContent = addMessage('assistant', '');
                            }
                            
                            fullResponse += data.chunk;
                            // Update with markdown rendering + sanitization
                            if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
                                const rawHTML = marked.parse(fullResponse);
                                const cleanHTML = DOMPurify.sanitize(rawHTML, {
                                    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                                                  'ul', 'ol', 'li', 'code', 'pre', 'blockquote', 'a', 'hr'],
                                    ALLOWED_ATTR: ['href', 'target', 'rel', 'class']
                                });
                                assistantContent.innerHTML = cleanHTML;
                            } else {
                                assistantContent.textContent = fullResponse;
                            }
                            // Only auto-scroll if user is already at bottom
                            if (shouldAutoScroll()) {
                                scrollToBottom();
                            }
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
        hideTyping();
    } finally {
        hideTyping();
        isStreaming = false;
        sendButton.disabled = false;
        messageInput.focus();
    }
}

// === Event Listeners ===
console.log('📦 SIDEBAR.JS VERSION: 2025-10-29-17:35 🆕');
console.log('🔗 Setting up event listeners');
console.log('sendButton exists?', sendButton !== null);
console.log('messageInput exists?', messageInput !== null);
console.log('sendButton element:', sendButton);
console.log('messageInput element:', messageInput);

if (sendButton) {
    sendButton.addEventListener('click', (e) => {
        console.log('🖱️ SEND BUTTON CLICKED!');
        e.preventDefault(); // Prevent any default behavior
        e.stopPropagation(); // Stop event bubbling
        console.log('🛡️ Default prevented, propagation stopped');
        sendMessage();
    });
    console.log('✅ Click listener added to send button');
} else {
    console.error('❌ sendButton is NULL - cannot add event listener!');
}

if (messageInput) {
    messageInput.addEventListener('keypress', (e) => {
        console.log('⌨️ KEY PRESSED:', e.key);
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            e.stopPropagation();
            console.log('✅ ENTER KEY - SENDING MESSAGE!');
            sendMessage();
        }
    });
    console.log('✅ Keypress listener added to message input');
} else {
    console.error('❌ messageInput is NULL - cannot add event listener!');
}

// iOS Safari: Scroll to top when keyboard closes to show header
messageInput.addEventListener('blur', () => {
    setTimeout(() => {
        window.scrollTo(0, 0);
    }, 100);
});

// === THEME TOGGLE ===
const themeToggle = document.getElementById('themeToggle');

// Get current theme from DOM (set by inline script)
let currentTheme = document.documentElement.getAttribute('data-theme') || 'light';

// Toggle theme function
function toggleTheme() {
    currentTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', currentTheme);
    localStorage.setItem('theme', currentTheme);
    console.log(`🌓 Theme switched to: ${currentTheme}`);
}

// Add click listener to toggle button
if (themeToggle) {
    themeToggle.addEventListener('click', toggleTheme);
    console.log('✅ Theme toggle button initialized');
} else {
    console.error('❌ Theme toggle button not found!');
}

// === Initialize ===
// Check if sidebar should be closed on mobile by default
if (window.innerWidth <= 768) {
    sidebar.classList.add('closed');
}

// Load conversations on startup
loadAllConversations();
