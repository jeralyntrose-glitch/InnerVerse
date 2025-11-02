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
let selectedImages = []; // Changed to array for multiple images

// File validation constants
// Target 3MB for file size because base64 encoding adds ~33% (3MB → 4MB after encoding, safely under 5MB limit)
const MAX_FILE_SIZE = 3 * 1024 * 1024; // 3MB in bytes (accounts for base64 inflation)
const MAX_IMAGES = 5; // Maximum number of images per message
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

// Validate image file (basic checks only - size handled by compression)
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
    
    return true;
}

// Compress image if over size limits using canvas
async function compressImage(file) {
    // GIF/WebP: Allow up to 3.75MB (will be ~5MB after base64 encoding)
    // JPEG/PNG: Target 3MB (will be ~4MB after base64 encoding)
    const isAnimatedFormat = file.type === 'image/gif' || file.type === 'image/webp';
    const sizeLimit = isAnimatedFormat ? 3.75 * 1024 * 1024 : MAX_FILE_SIZE;
    
    // If already under appropriate limit, return as-is
    if (file.size <= sizeLimit) {
        return file;
    }
    
    // GIF/WebP over 3.75MB: Don't compress (would lose animation), reject instead
    if (isAnimatedFormat) {
        throw new Error('GIF/WebP images must be under 3.75MB. Please upload a smaller file.');
    }
    
    console.log(`🗜️ Compressing image: ${file.name} (${formatFileSize(file.size)})`);
    
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        
        reader.onload = (e) => {
            const img = new Image();
            
            img.onload = () => {
                // Create canvas
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                
                // Calculate new dimensions (maintain aspect ratio)
                let width = img.width;
                let height = img.height;
                const maxDimension = 2048; // Max width or height
                
                // Resize if too large
                if (width > maxDimension || height > maxDimension) {
                    if (width > height) {
                        height = (height / width) * maxDimension;
                        width = maxDimension;
                    } else {
                        width = (width / height) * maxDimension;
                        height = maxDimension;
                    }
                }
                
                canvas.width = width;
                canvas.height = height;
                
                // Draw image on canvas
                ctx.drawImage(img, 0, 0, width, height);
                
                // Determine output format (preserve PNG if source was PNG for transparency)
                const outputFormat = file.type === 'image/png' ? 'image/png' : 'image/jpeg';
                const fileExtension = outputFormat === 'image/png' ? '.png' : '.jpg';
                
                // Try different quality levels to get under 4MB
                let quality = 0.9;
                const tryCompress = () => {
                    canvas.toBlob((blob) => {
                        if (!blob) {
                            reject(new Error('Compression failed'));
                            return;
                        }
                        
                        console.log(`   Quality ${quality.toFixed(1)}: ${formatFileSize(blob.size)}`);
                        
                        // If still too large and quality can be reduced, try again
                        if (blob.size > MAX_FILE_SIZE && quality > 0.5) {
                            quality -= 0.1;
                            tryCompress();
                        } else if (blob.size > MAX_FILE_SIZE) {
                            // Even at lowest quality, still too large
                            reject(new Error('Image too large. Please upload a smaller image (under 3MB).'));
                        } else {
                            // Success! Convert blob to file with appropriate extension
                            const originalName = file.name.replace(/\.[^.]+$/, '');
                            const compressedFile = new File([blob], originalName + fileExtension, {
                                type: outputFormat,
                                lastModified: Date.now()
                            });
                            console.log(`✅ Compressed: ${formatFileSize(file.size)} → ${formatFileSize(compressedFile.size)}`);
                            resolve(compressedFile);
                        }
                    }, outputFormat, quality);
                };
                
                tryCompress();
            };
            
            img.onerror = () => reject(new Error('Failed to load image'));
            img.src = e.target.result;
        };
        
        reader.onerror = () => reject(new Error('Failed to read file'));
        reader.readAsDataURL(file);
    });
}

// Upload button click handler
uploadButton.addEventListener('click', () => {
    imageUpload.click();
});

// Show multi-image preview with thumbnails
async function showMultiImagePreview() {
    const count = selectedImages.length;
    
    if (count === 0) {
        clearImagePreview();
        return;
    }
    
    // Build header with count and clear button
    const plural = count > 1 ? 's' : '';
    let html = `
        <div class="multi-image-preview">
            <div class="multi-image-header">
                <span class="image-count">${count} image${plural} selected</span>
                <button class="clear-all-btn" id="clearAllBtn">× Clear All</button>
            </div>
            <div class="image-thumbnail-list" id="thumbnailList">
    `;
    
    // Generate thumbnails (we'll add them after rendering)
    html += `
            </div>
        </div>
    `;
    
    imagePreviewContainer.innerHTML = html;
    imagePreviewContainer.style.display = 'block';
    
    // Update placeholder
    messageInput.placeholder = 'Add a message (optional)...';
    
    // Now load thumbnails asynchronously
    const thumbnailList = document.getElementById('thumbnailList');
    
    for (let i = 0; i < selectedImages.length; i++) {
        const file = selectedImages[i];
        
        // Read file as data URL
        const reader = new FileReader();
        const dataUrl = await new Promise((resolve) => {
            reader.onload = (e) => resolve(e.target.result);
            reader.readAsDataURL(file);
        });
        
        // Create thumbnail element
        const thumbItem = document.createElement('div');
        thumbItem.className = 'image-thumbnail-item';
        thumbItem.dataset.index = i;
        thumbItem.innerHTML = `
            <img src="${dataUrl}" class="image-thumbnail-thumb" alt="Image ${i + 1}">
            <button class="remove-thumb-btn" data-index="${i}">×</button>
        `;
        
        thumbnailList.appendChild(thumbItem);
    }
    
    // Add event listeners
    document.getElementById('clearAllBtn').addEventListener('click', clearImagePreview);
    
    // Add remove button listeners for each thumbnail
    document.querySelectorAll('.remove-thumb-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const index = parseInt(e.target.dataset.index);
            removeImageAtIndex(index);
        });
    });
}

// Remove image at specific index
function removeImageAtIndex(index) {
    console.log(`🗑️ Removing image at index ${index}`);
    
    // Remove from array
    selectedImages.splice(index, 1);
    
    // Update file input (rebuild FileList)
    const dataTransfer = new DataTransfer();
    selectedImages.forEach(file => dataTransfer.items.add(file));
    imageUpload.files = dataTransfer.files;
    
    // Refresh preview
    if (selectedImages.length > 0) {
        showMultiImagePreview();
    } else {
        clearImagePreview();
    }
    
    console.log(`✅ ${selectedImages.length} image(s) remaining`);
}

// Clear image preview
function clearImagePreview() {
    selectedImages = [];
    imagePreviewContainer.innerHTML = '';
    imagePreviewContainer.style.display = 'none';
    imageUpload.value = '';
    uploadButton.classList.remove('file-selected');
    messageInput.placeholder = 'Type your message...';
}

// File input change handler - NOW SUPPORTS MULTIPLE IMAGES
imageUpload.addEventListener('change', async (e) => {
    const files = Array.from(e.target.files);
    
    if (files.length === 0) {
        return;
    }
    
    // ===  VALIDATION: Max 5 images ===
    if (files.length > MAX_IMAGES) {
        showUploadError(`Maximum ${MAX_IMAGES} images allowed. You selected ${files.length}.`);
        imageUpload.value = '';
        return;
    }
    
    console.log(`📷 Selected ${files.length} image(s)`);
    
    // === VALIDATION: Check each file type and size ===
    for (const file of files) {
        // Check type
        if (!ALLOWED_TYPES.includes(file.type)) {
            showUploadError(`${file.name} is not a supported image type. Use JPEG, PNG, GIF, or WebP.`);
            imageUpload.value = '';
            return;
        }
        
        // Check raw size (before compression) - reject if over 10MB
        if (file.size > 10 * 1024 * 1024) {
            showUploadError(`${file.name} is too large (over 10MB). Please use smaller images.`);
            imageUpload.value = '';
            return;
        }
    }
    
    console.log('✅ All files passed validation');
    
    // === COMPRESS AND PROCESS ALL IMAGES ===
    try {
        selectedImages = [];
        
        for (const file of files) {
            console.log(`📷 Processing: ${file.name} (${formatFileSize(file.size)})`);
            
            // Compress image if needed
            const processedFile = await compressImage(file);
            
            if (processedFile.size !== file.size) {
                const reduction = ((1 - processedFile.size/file.size) * 100).toFixed(1);
                console.log(`✂️ Compressed ${file.name} by ${reduction}%`);
            }
            
            selectedImages.push(processedFile);
        }
        
        console.log(`✅ Processed ${selectedImages.length} image(s) successfully`);
        
        // Update UI - show all previews with thumbnails
        uploadButton.classList.add('file-selected');
        await showMultiImagePreview();
        
    } catch (error) {
        console.error('❌ Image processing error:', error);
        showUploadError(error.message);
        imageUpload.value = '';
        selectedImages = [];
    }
});

// === Sidebar Toggle ===
burgerMenu.addEventListener('click', () => {
    sidebar.classList.toggle('closed');
    burgerMenu.classList.toggle('sidebar-open');
    
    // Lock body scroll when sidebar is open on mobile
    if (!sidebar.classList.contains('closed')) {
        document.body.style.overflow = 'hidden';
    } else {
        document.body.style.overflow = '';
    }
});

// Close sidebar when clicking outside on mobile
document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768) {
        if (!sidebar.contains(e.target) && !burgerMenu.contains(e.target) && !sidebar.classList.contains('closed')) {
            sidebar.classList.add('closed');
            burgerMenu.classList.remove('sidebar-open');
            document.body.style.overflow = ''; // Restore body scroll
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
        document.body.style.overflow = ''; // Restore body scroll
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
        document.body.style.overflow = ''; // Restore body scroll
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

// Smart auto-scroll: Keep AI text visible with 100px clearance below
function scrollToKeepAIVisible() {
    // Find the last AI message
    const aiMessages = messagesDiv.querySelectorAll('.message.assistant');
    if (aiMessages.length === 0) {
        scrollToBottom();
        return;
    }
    
    const lastAIMessage = aiMessages[aiMessages.length - 1];
    
    // Get the bottom position of the AI message relative to the scrollable container
    const messageBottom = lastAIMessage.offsetTop + lastAIMessage.offsetHeight;
    
    // Calculate scroll position to maintain 100px clearance below the AI message
    const containerHeight = messagesDiv.clientHeight;
    const targetScroll = messageBottom - containerHeight + 100; // 100px clearance
    
    // Only scroll if we need to (AI message is below visible area)
    if (messagesDiv.scrollTop < targetScroll) {
        messagesDiv.scrollTo({
            top: targetScroll,
            behavior: 'smooth'
        });
    }
}

// ChatGPT-style scroll: Show user message at top with room for AI response below
function scrollToShowUserMessage() {
    // Find the last user message
    const userMessages = messagesDiv.querySelectorAll('.message.user');
    if (userMessages.length === 0) {
        scrollToBottom();
        return;
    }
    
    const lastUserMessage = userMessages[userMessages.length - 1];
    
    // Scroll so the user message appears near the top with room below for AI
    // offsetTop gives position relative to scrollable container
    const targetScroll = lastUserMessage.offsetTop - 20; // 20px from top for breathing room
    
    messagesDiv.scrollTop = targetScroll;
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

// Copy message to clipboard with improved fallback
async function copyMessageToClipboard(messageText, isAIMessage, button) {
    console.log('📋 copyMessageToClipboard called', { 
        isAIMessage, 
        textLength: messageText?.length || 0,
        hasText: !!messageText,
        preview: messageText?.substring(0, 100)
    });
    
    if (!messageText) {
        console.error('❌ No message text to copy!');
        showCopyError(button);
        return;
    }
    
    // Keep formatting (headers, emojis, etc.) - don't strip markdown
    const textToCopy = messageText;
    console.log('📋 Text prepared for copy', { 
        length: textToCopy.length,
        preview: textToCopy.substring(0, 100)
    });
    
    // Try modern Clipboard API first
    try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            console.log('📋 Attempting Clipboard API...');
            await navigator.clipboard.writeText(textToCopy);
            console.log('✅ Clipboard API success!');
            showCopySuccess(button);
            return;
        }
    } catch (err) {
        console.error('❌ Clipboard API error:', err.message, err);
    }
    
    // Fallback method for all cases where Clipboard API isn't available or fails
    console.log('📋 Using fallback copy method');
    fallbackCopy(textToCopy, button);
}

// Improved fallback copy method
function fallbackCopy(text, button) {
    console.log('📋 Fallback copy starting...');
    const textarea = document.createElement('textarea');
    textarea.value = text;
    
    // Better positioning to ensure it works on all browsers
    textarea.style.position = 'fixed';
    textarea.style.top = '0';
    textarea.style.left = '0';
    textarea.style.width = '2em';
    textarea.style.height = '2em';
    textarea.style.padding = '0';
    textarea.style.border = 'none';
    textarea.style.outline = 'none';
    textarea.style.boxShadow = 'none';
    textarea.style.background = 'transparent';
    textarea.style.opacity = '0';
    textarea.setAttribute('readonly', '');
    
    document.body.appendChild(textarea);
    
    try {
        // Focus and select the textarea
        textarea.focus();
        textarea.select();
        
        // For iOS
        textarea.setSelectionRange(0, 999999);
        
        // Execute copy command
        const success = document.execCommand('copy');
        console.log('📋 execCommand result:', success);
        
        if (success) {
            console.log('✅ Fallback copy successful!');
            showCopySuccess(button);
        } else {
            console.error('❌ execCommand returned false');
            showCopyError(button);
        }
    } catch (err) {
        console.error('❌ Fallback copy exception:', err);
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
    
    // === Phase 9: REMOVE entire [FOLLOW-UP: ...] from AI message content (shown separately as green button) ===
    if (role === 'assistant' && content) {
        content = content.replace(/\[FOLLOW-UP:.*?\]/g, '').trim();
    }
    
    // === Phase 6: Add image(s) if provided (for user messages) ===
    if (imageFile && role === 'user') {
        // Handle both single image (backward compat) and multiple images
        const images = Array.isArray(imageFile) ? imageFile : [imageFile];
        
        // Create container for images if multiple
        if (images.length > 1) {
            const imageContainer = document.createElement('div');
            imageContainer.style.cssText = 'display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; margin-bottom: 8px;';
            
            images.forEach((img, index) => {
                const reader = new FileReader();
                reader.onload = (e) => {
                    const imgElement = document.createElement('img');
                    imgElement.src = e.target.result;
                    imgElement.className = 'message-image';
                    imgElement.style.cssText = 'width: 100%; height: auto; border-radius: 8px; object-fit: cover; max-height: 200px;';
                    imgElement.alt = `Image ${index + 1}`;
                    imageContainer.appendChild(imgElement);
                };
                reader.readAsDataURL(img);
            });
            
            contentDiv.insertBefore(imageContainer, contentDiv.firstChild);
        } else {
            // Single image - keep existing behavior
            const reader = new FileReader();
            reader.onload = (e) => {
                const imgElement = document.createElement('img');
                imgElement.src = e.target.result;
                imgElement.className = 'message-image';
                imgElement.style.cssText = 'max-width: 300px; width: 100%; height: auto; border-radius: 12px; margin-bottom: 8px; display: block;';
                contentDiv.insertBefore(imgElement, contentDiv.firstChild);
            };
            reader.readAsDataURL(images[0]);
        }
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
    
    // IMPORTANT: Capture content in closure to avoid reference issues when loading multiple messages
    const messageCopy = String(content || '');
    const roleCopy = String(role);
    
    // Add click handler with closure-captured values (arrow function to preserve context)
    copyButton.addEventListener('click', (e) => {
        e.stopPropagation();
        e.preventDefault();
        console.log('📋 Copy button clicked!', { 
            textLength: messageCopy.length, 
            role: roleCopy, 
            preview: messageCopy.substring(0, 50) 
        });
        copyMessageToClipboard(messageCopy, roleCopy === 'assistant', copyButton);
    });
    
    // Add keyboard support (Enter and Space)
    copyButton.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            copyMessageToClipboard(messageCopy, roleCopy === 'assistant', copyButton);
        }
    });
    
    messageDiv.appendChild(copyButton);
    
    // === Phase 9: Add AI-suggested follow-up question for conversation continuation ===
    if (followUpQuestion && role === 'assistant') {
        const followUpContainer = document.createElement('div');
        followUpContainer.className = 'follow-up-question-container';
        followUpContainer.style.cssText = 'margin-top: 12px; padding: 10px 14px; background: rgba(16, 163, 127, 0.08); border-radius: 8px; border-left: 3px solid #10A37F;';
        
        const questionButton = document.createElement('button');
        questionButton.className = 'suggested-question';
        questionButton.textContent = followUpQuestion;
        questionButton.style.cssText = 'background: none; border: none; color: #10A37F; font-size: 14px; cursor: pointer; text-align: left; width: 100%; padding: 0; font-family: inherit;';
        
        questionButton.addEventListener('click', () => {
            messageInput.value = followUpQuestion;
            messageInput.focus();
            messageInput.style.height = 'auto';
            messageInput.style.height = messageInput.scrollHeight + 'px';
        });
        
        followUpContainer.appendChild(questionButton);
        messageDiv.appendChild(followUpContainer);
    }
    
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
    const hasImages = selectedImages.length > 0;
    
    console.log('📝 Message:', message, '| hasImages:', hasImages, '| imageCount:', selectedImages.length, '| isStreaming:', isStreaming, '| conversationId:', conversationId);
    
    // Allow sending if there's a message OR images
    if ((!message && !hasImages) || isStreaming || !conversationId) {
        console.log('❌ Blocked from sending - conditions not met');
        return;
    }

    messageInput.value = '';
    messageInput.style.height = 'auto'; // Reset textarea height
    isStreaming = true;
    sendButton.disabled = true;

    // Prepare message payload
    let messagePayload = { message: message || '' };
    
    // If there are images, convert ALL to base64 and add to payload
    if (hasImages) {
        console.log(`📤 Preparing to send ${selectedImages.length} image(s)`);
        
        try {
            const imageDataUrls = [];
            let totalSize = 0;
            
            // Convert all images to base64
            for (let i = 0; i < selectedImages.length; i++) {
                const image = selectedImages[i];
                console.log(`📤 Processing image ${i + 1}/${selectedImages.length}: ${image.name} (${formatFileSize(image.size)})`);
                
                const reader = new FileReader();
                const imageDataUrl = await new Promise((resolve, reject) => {
                    reader.onload = () => resolve(reader.result);
                    reader.onerror = reject;
                    reader.readAsDataURL(image);
                });
                
                imageDataUrls.push(imageDataUrl);
                totalSize += imageDataUrl.length;
            }
            
            // Send as array if multiple images, single string if one image (for backward compatibility)
            if (imageDataUrls.length === 1) {
                messagePayload.image = imageDataUrls[0];
            } else {
                messagePayload.images = imageDataUrls;
            }
            
            // Log transmission stats
            console.log(`📡 Sending ${imageDataUrls.length} image(s) - Total base64 size: ${totalSize.toLocaleString()} chars`);
            console.log(`💾 Estimated total size: ${formatFileSize(totalSize * 0.75)}`); // Base64 is ~33% larger
            
        } catch (error) {
            console.error('Error reading images:', error);
            showError('Failed to process images. Please try again.');
            isStreaming = false;
            sendButton.disabled = false;
            return;
        }
    }

    // Display user message (with all images)
    addMessage('user', message, hasImages ? selectedImages : null);
    
    // ChatGPT-style scroll: Show user message at top with room for AI response below
    setTimeout(() => scrollToShowUserMessage(), 50);
    
    // Clear image preview after adding to chat
    if (hasImages) {
        clearImagePreview();
    }
    
    // Show typing indicator
    showTyping();
    
    // Scroll again after typing indicator appears to ensure it's visible
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
                            // Strip [FOLLOW-UP: ...] brackets from display
                            let displayResponse = fullResponse.replace(/\[FOLLOW-UP:\s*/g, '').replace(/\]/g, '');
                            // Update with markdown rendering + sanitization
                            if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
                                const rawHTML = marked.parse(displayResponse);
                                const cleanHTML = DOMPurify.sanitize(rawHTML, {
                                    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                                                  'ul', 'ol', 'li', 'code', 'pre', 'blockquote', 'a', 'hr'],
                                    ALLOWED_ATTR: ['href', 'target', 'rel', 'class']
                                });
                                assistantContent.innerHTML = cleanHTML;
                            } else {
                                assistantContent.textContent = displayResponse;
                            }
                            // Smart auto-scroll: Keep AI text visible with 100px clearance
                            scrollToKeepAIVisible();
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
            // On mobile, allow Enter to create new lines
            // Only send on desktop
            const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent) || window.innerWidth <= 768;
            
            if (!isMobile) {
                // Desktop: Enter sends, Shift+Enter for new line
                e.preventDefault();
                e.stopPropagation();
                console.log('✅ ENTER KEY (Desktop) - SENDING MESSAGE!');
                sendMessage();
            } else {
                // Mobile: Enter creates new line, use send button to send
                console.log('📱 ENTER KEY (Mobile) - NEW LINE');
                // Let default behavior happen (new line)
            }
        }
    });
    console.log('✅ Keypress listener added to message input');
} else {
    console.error('❌ messageInput is NULL - cannot add event listener!');
}

// Toggle keyboard-active class to remove white space above input
const chatContainer = document.querySelector('.chat-container');
if (chatContainer && messageInput) {
    messageInput.addEventListener('focus', () => {
        chatContainer.classList.add('keyboard-active');
    });
    
    messageInput.addEventListener('blur', () => {
        chatContainer.classList.remove('keyboard-active');
        // iOS Safari: Scroll to top when keyboard closes to show header
        setTimeout(() => {
            window.scrollTo(0, 0);
        }, 100);
    });
}

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

// === SCROLL TO BOTTOM BUTTON ===
const scrollToBottomBtn = document.getElementById('scrollToBottomBtn');

// Check if user is at bottom of messages
function isAtBottom() {
    const threshold = 100; // pixels from bottom
    const scrollTop = messagesDiv.scrollTop;
    const scrollHeight = messagesDiv.scrollHeight;
    const clientHeight = messagesDiv.clientHeight;
    
    return (scrollHeight - scrollTop - clientHeight) < threshold;
}

// Update scroll button visibility
let scrollCheckTimeout;
function updateScrollButton() {
    if (isAtBottom()) {
        scrollToBottomBtn.classList.remove('visible');
    } else {
        scrollToBottomBtn.classList.add('visible');
    }
}

// Throttled scroll event listener
messagesDiv.addEventListener('scroll', () => {
    if (scrollCheckTimeout) return;
    
    scrollCheckTimeout = setTimeout(() => {
        updateScrollButton();
        scrollCheckTimeout = null;
    }, 100);
});

// Scroll to bottom when button clicked
scrollToBottomBtn.addEventListener('click', () => {
    messagesDiv.scrollTo({
        top: messagesDiv.scrollHeight,
        behavior: 'smooth'
    });
});

// Initial check
updateScrollButton();

// === Initialize ===
// Check if sidebar should be closed on mobile by default
if (window.innerWidth <= 768) {
    sidebar.classList.add('closed');
}

// Load conversations on startup
loadAllConversations();
