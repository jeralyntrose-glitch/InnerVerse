# PHASE 7.3: LESSON PAGE - PART 3 (JavaScript + Testing)

**Project:** InnerVerse - CS Joseph University  
**Phase:** 7.3 of 7 (Part 3 of 3 - FINAL)  
**Goal:** Complete JavaScript functionality + Testing  
**Prerequisites:** Phase 7.3 Part 1 ✅ Part 2 ✅ (Database + Backend + HTML + CSS working)

---

## 🎨 STEP 5: FRONTEND - JAVASCRIPT

### 5.1 Create static/lesson_page.js

**File:** `static/lesson_page.js`

```javascript
// ==============================================================================
// PHASE 7.3: LESSON PAGE - COMPLETE JAVASCRIPT
//
// Features:
// - Load lesson data from API
// - Render video or Skool message
// - Generate AI lesson content with fallbacks
// - Load and display transcript
// - AI chat with streaming responses
// - Mark lesson complete
// - Previous/Next navigation
// - Theme toggle
// - Mobile sidebar
// ==============================================================================

// ==============================================================================
// CONFIGURATION
// ==============================================================================

const CONFIG = {
    API_BASE: '',  // Same origin
    BACKEND_API: 'https://axis-of-mind.replit.app/query',
    BACKEND_KEY: 'axis_ZMEmIg-mAqwIhVELvOthykohrRufDX3VTskCV6VbxrU',
    RETRY_ATTEMPTS: 3,
    RETRY_DELAY: 1000,
    CHUNK_TIMEOUT: 30000  // 30 seconds for streaming timeout
};

// ==============================================================================
// STATE MANAGEMENT
// ==============================================================================

let state = {
    lessonId: null,
    lessonData: null,
    chatHistory: [],
    isGeneratingLesson: false,
    isGeneratingChat: false,
    transcriptLoaded: false,
    theme: 'dark'
};

// ==============================================================================
// INITIALIZATION
// ==============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 Lesson page initializing...');
    
    // Extract lesson ID from URL
    const pathParts = window.location.pathname.split('/');
    state.lessonId = parseInt(pathParts[pathParts.length - 1]);
    
    if (!state.lessonId || isNaN(state.lessonId)) {
        showError('Invalid lesson ID');
        return;
    }
    
    console.log(`📚 Loading lesson ${state.lessonId}`);
    
    // Initialize theme
    initTheme();
    
    // Setup event listeners
    setupEventListeners();
    
    // Load all data
    await Promise.all([
        loadLessonData(),
        loadChatHistory()
    ]);
    
    console.log('✅ Lesson page ready!');
});

// ==============================================================================
// THEME MANAGEMENT
// ==============================================================================

function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    state.theme = savedTheme;
    document.body.setAttribute('data-theme', savedTheme);
    updateThemeIcon();
}

function toggleTheme() {
    state.theme = state.theme === 'dark' ? 'light' : 'dark';
    document.body.setAttribute('data-theme', state.theme);
    localStorage.setItem('theme', state.theme);
    updateThemeIcon();
}

function updateThemeIcon() {
    const icon = document.querySelector('.theme-icon');
    if (icon) {
        icon.textContent = state.theme === 'dark' ? '☀️' : '🌙';
    }
}

// ==============================================================================
// EVENT LISTENERS
// ==============================================================================

function setupEventListeners() {
    // Theme toggle
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
    
    // Mobile hamburger menu
    const mobileToggle = document.getElementById('mobileMenuToggle');
    const sidebar = document.getElementById('lessonSidebar');
    const overlay = document.getElementById('sidebarOverlay');
    
    if (mobileToggle && sidebar && overlay) {
        mobileToggle.addEventListener('click', () => {
            sidebar.classList.toggle('active');
            overlay.classList.toggle('active');
        });
        
        overlay.addEventListener('click', () => {
            sidebar.classList.remove('active');
            overlay.classList.remove('active');
        });
    }
    
    // Chat input
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    
    if (chatInput && sendBtn) {
        sendBtn.addEventListener('click', () => sendMessage());
        
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
    
    // Mark complete button
    const markCompleteBtn = document.getElementById('markCompleteBtn');
    if (markCompleteBtn) {
        markCompleteBtn.addEventListener('click', markLessonComplete);
    }
    
    // Transcript toggle
    const transcriptToggle = document.getElementById('transcriptToggle');
    if (transcriptToggle) {
        transcriptToggle.addEventListener('click', toggleTranscript);
    }
}

// ==============================================================================
// LESSON DATA LOADING
// ==============================================================================

async function loadLessonData() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/lesson/${state.lessonId}`);
        
        if (!response.ok) {
            if (response.status === 404) {
                showError('Lesson not found');
                return;
            }
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        state.lessonData = data;
        
        console.log('📖 Lesson data loaded:', data.lesson.lesson_title);
        
        // Render all components
        renderBreadcrumb(data.lesson);
        renderHeader(data.lesson);
        renderVideo(data.lesson);
        renderSidebar(data.season_lessons, data.lesson.lesson_id);
        renderNavigation(data.navigation);
        
        // Generate AI lesson content
        await generateLessonContent(data.lesson);
        
        // Load transcript if available
        loadTranscript(data.lesson.transcript_id);
        
        // Update mark complete button
        updateMarkCompleteButton(data.progress.completed);
        
    } catch (error) {
        console.error('❌ Error loading lesson:', error);
        showError('Failed to load lesson data');
    }
}

// ==============================================================================
// RENDERING FUNCTIONS
// ==============================================================================

function renderBreadcrumb(lesson) {
    const moduleEl = document.getElementById('breadcrumbModule');
    const seasonEl = document.getElementById('breadcrumbSeason');
    
    if (moduleEl) {
        moduleEl.textContent = `Module ${lesson.module_number}: ${lesson.module_name}`;
    }
    
    if (seasonEl) {
        seasonEl.innerHTML = `<a href="/season/${lesson.season_number}" class="breadcrumb-link">Season ${lesson.season_number}: ${lesson.season_name}</a>`;
    }
}

function renderHeader(lesson) {
    const metaEl = document.getElementById('lessonMetaSmall');
    const titleEl = document.getElementById('lessonTitle');
    
    if (metaEl) {
        metaEl.textContent = `Season ${lesson.season_number}, Lesson ${lesson.lesson_number}`;
    }
    
    if (titleEl) {
        titleEl.textContent = lesson.lesson_title;
    }
}

function renderVideo(lesson) {
    const videoSection = document.getElementById('videoSection');
    if (!videoSection) return;
    
    if (lesson.youtube_url && lesson.has_video) {
        // Extract video ID from YouTube URL
        const videoId = extractYouTubeId(lesson.youtube_url);
        
        if (videoId) {
            videoSection.innerHTML = `
                <div class="video-container">
                    <iframe
                        src="https://www.youtube.com/embed/${videoId}"
                        frameborder="0"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                        allowfullscreen
                    ></iframe>
                </div>
            `;
        } else {
            renderSkoolMessage(videoSection, lesson);
        }
    } else {
        renderSkoolMessage(videoSection, lesson);
    }
}

function renderSkoolMessage(container, lesson) {
    container.innerHTML = `
        <div class="skool-message">
            <div class="skool-icon">📺</div>
            <h3>Premium Content</h3>
            <p>This lesson is from CS Joseph's paid Skool platform.</p>
            <p class="video-title">
                <strong>Watch on Skool:</strong><br>
                Season ${lesson.season_number} - ${lesson.lesson_title}
            </p>
            <a href="https://www.skool.com/csjoseph" 
               target="_blank" 
               class="skool-button">
                Visit CS Joseph's Skool →
            </a>
        </div>
    `;
}

function extractYouTubeId(url) {
    if (!url) return null;
    
    // Handle different YouTube URL formats
    const patterns = [
        /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/,
        /^([a-zA-Z0-9_-]{11})$/  // Just the ID
    ];
    
    for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match && match[1]) {
            return match[1];
        }
    }
    
    return null;
}

function renderSidebar(lessons, currentLessonId) {
    const sidebarContent = document.getElementById('sidebarContent');
    if (!sidebarContent) return;
    
    if (!lessons || lessons.length === 0) {
        sidebarContent.innerHTML = '<p style="color: var(--text-muted); text-align: center;">No lessons found</p>';
        return;
    }
    
    const html = lessons.map(lesson => {
        const isActive = lesson.lesson_id === currentLessonId;
        const statusIcon = lesson.completed ? '✓' : (isActive ? '▶' : '□');
        
        return `
            <div class="sidebar-lesson-item ${isActive ? 'active' : ''}" 
                 onclick="navigateToLesson(${lesson.lesson_id})">
                <span class="lesson-status-icon">${statusIcon}</span>
                <div class="sidebar-lesson-info">
                    <div class="sidebar-lesson-number">Lesson ${lesson.lesson_number}</div>
                    <div class="sidebar-lesson-title">${lesson.lesson_title}</div>
                    ${lesson.duration ? `<div class="sidebar-lesson-duration">${lesson.duration}</div>` : ''}
                </div>
            </div>
        `;
    }).join('');
    
    sidebarContent.innerHTML = html;
}

function renderNavigation(navigation) {
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    
    if (prevBtn) {
        prevBtn.disabled = !navigation.has_prev;
        if (navigation.has_prev) {
            prevBtn.onclick = () => navigateToLesson(navigation.prev_lesson_id);
        }
    }
    
    if (nextBtn) {
        nextBtn.disabled = !navigation.has_next;
        if (navigation.has_next) {
            nextBtn.onclick = () => navigateToLesson(navigation.next_lesson_id);
        }
    }
}

function navigateToLesson(lessonId) {
    window.location.href = `/lesson/${lessonId}`;
}

// ==============================================================================
// AI LESSON CONTENT GENERATION
// ==============================================================================

async function generateLessonContent(lesson) {
    const contentEl = document.getElementById('lessonContent');
    if (!contentEl) return;
    
    if (state.isGeneratingLesson) {
        console.log('⏳ Already generating lesson content...');
        return;
    }
    
    state.isGeneratingLesson = true;
    
    try {
        console.log('🤖 Generating AI lesson content...');
        
        // Show loading state
        contentEl.innerHTML = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p>Generating lesson content from transcript...</p>
            </div>
        `;
        
        // Query backend API
        const response = await fetch(CONFIG.BACKEND_API, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${CONFIG.BACKEND_KEY}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                document_id: "",
                question: `Create a comprehensive lesson summary from the transcript with ID "${lesson.transcript_id}". 

Include:
- Key concepts and main teaching points
- Practical examples from the video
- Actionable insights
- Important quotes or memorable moments

Format with clear headers and organized sections. Make it educational and engaging.`,
                tags: [lesson.transcript_id, `season${lesson.season_number}`]
            })
        });
        
        if (!response.ok) {
            throw new Error(`Backend API error: ${response.status}`);
        }
        
        // Read streamed response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullResponse = '';
        
        contentEl.innerHTML = '';  // Clear loading state
        
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            fullResponse += chunk;
            
            // Update UI with accumulated response (formatted as markdown)
            contentEl.innerHTML = formatMarkdown(fullResponse);
        }
        
        // Check if we got a valid response
        if (!fullResponse.trim()) {
            throw new Error('Empty response from backend');
        }
        
        console.log('✅ Lesson content generated successfully');
        
        // Show mark complete button
        const markCompleteBtn = document.getElementById('markCompleteBtn');
        if (markCompleteBtn) {
            markCompleteBtn.style.display = 'inline-flex';
        }
        
    } catch (error) {
        console.error('❌ Error generating lesson content:', error);
        
        // Show friendly fallback
        contentEl.innerHTML = `
            <div class="coming-soon-state">
                <div class="icon">📝</div>
                <h4>Lesson Content Coming Soon</h4>
                <p>This lesson's transcript hasn't been processed yet. Check back soon!</p>
                <p style="margin-top: 16px; font-size: 13px;">
                    <strong>Transcript ID:</strong> ${lesson.transcript_id}
                </p>
            </div>
        `;
        
        // Still show mark complete button
        const markCompleteBtn = document.getElementById('markCompleteBtn');
        if (markCompleteBtn) {
            markCompleteBtn.style.display = 'inline-flex';
        }
    } finally {
        state.isGeneratingLesson = false;
    }
}

// ==============================================================================
// MARKDOWN FORMATTING
// ==============================================================================

function formatMarkdown(text) {
    if (!text) return '';
    
    let html = text;
    
    // Headers
    html = html.replace(/^### (.*$)/gim, '<h4>$1</h4>');
    html = html.replace(/^## (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^# (.*$)/gim, '<h3>$1</h3>');
    
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__(.*?)__/g, '<strong>$1</strong>');
    
    // Italic
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    html = html.replace(/_(.*?)_/g, '<em>$1</em>');
    
    // Code
    html = html.replace(/`(.*?)`/g, '<code>$1</code>');
    
    // Lists
    html = html.replace(/^\* (.*$)/gim, '<li>$1</li>');
    html = html.replace(/^- (.*$)/gim, '<li>$1</li>');
    
    // Paragraphs
    html = html.split('\n\n').map(para => {
        if (para.startsWith('<h') || para.startsWith('<li')) {
            return para;
        }
        return para.trim() ? `<p>${para}</p>` : '';
    }).join('\n');
    
    return html;
}

// ==============================================================================
// TRANSCRIPT LOADING
// ==============================================================================

async function loadTranscript(transcriptId) {
    if (!transcriptId) {
        console.log('⚠️ No transcript ID provided');
        return;
    }
    
    try {
        console.log(`📄 Loading transcript: ${transcriptId}`);
        
        // Query backend for transcript
        const response = await fetch(CONFIG.BACKEND_API, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${CONFIG.BACKEND_KEY}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                document_id: "",
                question: `Return the FULL TRANSCRIPT for transcript ID "${transcriptId}". Return ONLY the transcript text, no summaries or explanations.`,
                tags: [transcriptId]
            })
        });
        
        if (!response.ok) {
            throw new Error(`Backend API error: ${response.status}`);
        }
        
        // Read streamed response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullTranscript = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            fullTranscript += decoder.decode(value, { stream: true });
        }
        
        if (fullTranscript.trim()) {
            const transcriptText = document.getElementById('transcriptText');
            const transcriptToggle = document.getElementById('transcriptToggle');
            
            if (transcriptText) {
                transcriptText.textContent = fullTranscript;
                state.transcriptLoaded = true;
            }
            
            if (transcriptToggle) {
                transcriptToggle.disabled = false;
            }
            
            console.log('✅ Transcript loaded successfully');
        }
        
    } catch (error) {
        console.error('❌ Error loading transcript:', error);
    }
}

function toggleTranscript() {
    const toggleBtn = document.getElementById('transcriptToggle');
    const content = document.getElementById('transcriptContent');
    
    if (!toggleBtn || !content) return;
    
    const isOpen = content.style.display !== 'none';
    
    if (isOpen) {
        content.style.display = 'none';
        toggleBtn.classList.remove('open');
        toggleBtn.querySelector('.toggle-text').textContent = 'Show Transcript';
    } else {
        content.style.display = 'block';
        toggleBtn.classList.add('open');
        toggleBtn.querySelector('.toggle-text').textContent = 'Hide Transcript';
    }
}

// ==============================================================================
// CHAT FUNCTIONALITY
// ==============================================================================

async function loadChatHistory() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/lesson/${state.lessonId}/chat`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        state.chatHistory = data.messages || [];
        
        console.log(`💬 Loaded ${state.chatHistory.length} chat messages`);
        
        renderChatHistory();
        
    } catch (error) {
        console.error('❌ Error loading chat history:', error);
        state.chatHistory = [];
    }
}

function renderChatHistory() {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    if (state.chatHistory.length === 0) {
        chatMessages.innerHTML = `
            <div style="text-align: center; color: var(--text-muted); padding: 40px 20px;">
                <p>No messages yet. Ask a question about this lesson!</p>
            </div>
        `;
        return;
    }
    
    chatMessages.innerHTML = state.chatHistory.map(msg => {
        const time = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '';
        
        return `
            <div class="message ${msg.role}-message">
                <div class="message-content">${escapeHtml(msg.content)}</div>
                ${time ? `<div class="message-time">${time}</div>` : ''}
            </div>
        `;
    }).join('');
    
    scrollChatToBottom();
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    
    if (!input || !sendBtn) return;
    
    const message = input.value.trim();
    
    if (!message || state.isGeneratingChat) return;
    
    // Disable input
    input.disabled = true;
    sendBtn.disabled = true;
    state.isGeneratingChat = true;
    
    try {
        // Add user message
        const userMessage = {
            role: 'user',
            content: message,
            timestamp: new Date().toISOString()
        };
        
        state.chatHistory.push(userMessage);
        
        // Clear input
        input.value = '';
        
        // Save user message
        await saveChatMessage(userMessage);
        
        // Render immediately
        renderChatHistory();
        
        // Show typing indicator
        showTypingIndicator();
        
        // Get lesson context
        const lessonContext = state.lessonData?.lesson ? 
            `This question is about the lesson: "${state.lessonData.lesson.lesson_title}" (Season ${state.lessonData.lesson.season_number}).` : '';
        
        // Query backend
        const response = await fetch(CONFIG.BACKEND_API, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${CONFIG.BACKEND_KEY}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                document_id: "",
                question: `${lessonContext}\n\nUser question: ${message}`,
                tags: state.lessonData?.lesson ? 
                    [state.lessonData.lesson.transcript_id, `season${state.lessonData.lesson.season_number}`] : 
                    []
            })
        });
        
        if (!response.ok) {
            throw new Error(`Backend API error: ${response.status}`);
        }
        
        // Stream AI response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let aiResponse = '';
        
        // Remove typing indicator
        removeTypingIndicator();
        
        // Create AI message container
        const aiMessageId = createAIMessageContainer();
        
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            aiResponse += chunk;
            
            // Update AI message in real-time
            updateAIMessage(aiMessageId, aiResponse);
        }
        
        // Save AI response
        const aiMessage = {
            role: 'assistant',
            content: aiResponse,
            timestamp: new Date().toISOString()
        };
        
        state.chatHistory.push(aiMessage);
        await saveChatMessage(aiMessage);
        
        console.log('✅ Chat message sent and received');
        
    } catch (error) {
        console.error('❌ Error sending message:', error);
        
        removeTypingIndicator();
        
        // Show error message
        const errorMessage = {
            role: 'assistant',
            content: 'Sorry, I encountered an error processing your question. Please try again.',
            timestamp: new Date().toISOString()
        };
        
        state.chatHistory.push(errorMessage);
        renderChatHistory();
        
    } finally {
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
        state.isGeneratingChat = false;
    }
}

function showTypingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    const indicator = document.createElement('div');
    indicator.id = 'typingIndicator';
    indicator.className = 'typing-indicator';
    indicator.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;
    
    chatMessages.appendChild(indicator);
    scrollChatToBottom();
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

function createAIMessageContainer() {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return null;
    
    const messageId = `ai-message-${Date.now()}`;
    const messageEl = document.createElement('div');
    messageEl.id = messageId;
    messageEl.className = 'message ai-message';
    messageEl.innerHTML = `
        <div class="message-content"></div>
    `;
    
    chatMessages.appendChild(messageEl);
    scrollChatToBottom();
    
    return messageId;
}

function updateAIMessage(messageId, content) {
    const messageEl = document.getElementById(messageId);
    if (!messageEl) return;
    
    const contentEl = messageEl.querySelector('.message-content');
    if (contentEl) {
        contentEl.textContent = content;
        scrollChatToBottom();
    }
}

async function saveChatMessage(message) {
    try {
        await fetch(`${CONFIG.API_BASE}/api/lesson/${state.lessonId}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(message)
        });
    } catch (error) {
        console.error('❌ Error saving chat message:', error);
    }
}

function scrollChatToBottom() {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// ==============================================================================
// MARK LESSON COMPLETE
// ==============================================================================

async function markLessonComplete() {
    const btn = document.getElementById('markCompleteBtn');
    if (!btn) return;
    
    if (btn.classList.contains('completed')) {
        return;
    }
    
    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/lesson/${state.lessonId}/complete`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        console.log('✅ Lesson marked complete');
        
        updateMarkCompleteButton(true);
        
        // Update sidebar
        if (state.lessonData) {
            const lessonInSidebar = state.lessonData.season_lessons.find(l => l.lesson_id === state.lessonId);
            if (lessonInSidebar) {
                lessonInSidebar.completed = true;
                renderSidebar(state.lessonData.season_lessons, state.lessonId);
            }
        }
        
    } catch (error) {
        console.error('❌ Error marking lesson complete:', error);
        alert('Failed to mark lesson complete. Please try again.');
    }
}

function updateMarkCompleteButton(completed) {
    const btn = document.getElementById('markCompleteBtn');
    if (!btn) return;
    
    if (completed) {
        btn.classList.add('completed');
        btn.querySelector('.btn-text').textContent = 'Completed';
        btn.disabled = true;
    } else {
        btn.classList.remove('completed');
        btn.querySelector('.btn-text').textContent = 'Mark as Complete';
        btn.disabled = false;
    }
}

// ==============================================================================
// UTILITY FUNCTIONS
// ==============================================================================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(message) {
    const main = document.querySelector('.lesson-main');
    if (main) {
        main.innerHTML = `
            <div style="text-align: center; padding: 80px 20px;">
                <div style="font-size: 48px; margin-bottom: 20px;">⚠️</div>
                <h2 style="margin-bottom: 10px;">Error</h2>
                <p style="color: var(--text-muted);">${message}</p>
                <a href="/" style="display: inline-block; margin-top: 30px; color: var(--accent-primary);">
                    ← Back to Dashboard
                </a>
            </div>
        `;
    }
}

// ==============================================================================
// END PHASE 7.3 JAVASCRIPT
// ==============================================================================
```

---

## ✅ STEP 6: COMPLETE TESTING CHECKLIST

### 6.1 Database Tests

```sql
-- Check lesson_chats table exists
\d lesson_chats

-- Verify indexes
\di lesson_chats*

-- Test insert
INSERT INTO lesson_chats (lesson_id, messages)
VALUES (4, '[{"role":"user","content":"test","timestamp":"2025-11-14T10:00:00"}]'::jsonb);

-- Test select
SELECT * FROM lesson_chats WHERE lesson_id = 4;

-- Clean up test
DELETE FROM lesson_chats WHERE lesson_id = 4;
```

### 6.2 Backend API Tests

```bash
# Test lesson data endpoint
curl http://localhost:5000/api/lesson/4 | jq '.'
# Expected: JSON with lesson, progress, navigation, season_lessons

# Test chat history (empty)
curl http://localhost:5000/api/lesson/4/chat | jq '.'
# Expected: {"messages": []}

# Test save chat message
curl -X POST http://localhost:5000/api/lesson/4/chat \
  -H "Content-Type: application/json" \
  -d '{"role":"user","content":"test","timestamp":"2025-11-14T10:00:00"}' | jq '.'
# Expected: {"success": true}

# Test mark complete
curl -X POST http://localhost:5000/api/lesson/4/complete | jq '.'
# Expected: {"success": true, "completed": true}
```

### 6.3 Frontend Tests - Desktop

**Open:** `http://localhost:5000/lesson/4`

- [ ] Page loads without errors
- [ ] Lesson title displays correctly
- [ ] Breadcrumb shows: Dashboard > Module > Season
- [ ] Video embeds (if youtube_url exists)
  - [ ] OR Skool message shows (if no video)
- [ ] Sidebar shows all season lessons
  - [ ] Current lesson highlighted with ▶
  - [ ] Completed lessons show ✓
  - [ ] Click lesson → navigates correctly
- [ ] AI lesson content generates
  - [ ] Shows loading spinner initially
  - [ ] Content appears after generation
  - [ ] OR "Coming soon" fallback if transcript missing
- [ ] Transcript toggle works
  - [ ] Button disabled if no transcript
  - [ ] Click → expands/collapses
  - [ ] Content loads correctly
- [ ] Chat interface functional
  - [ ] Can type message
  - [ ] Enter key sends message
  - [ ] User message appears (blue, right-aligned)
  - [ ] Typing indicator shows
  - [ ] AI response streams in
  - [ ] AI message appears (gray, left-aligned)
  - [ ] Messages persist on page reload
- [ ] Mark complete button
  - [ ] Appears after lesson loads
  - [ ] Click → marks lesson complete
  - [ ] Button changes to "Completed" (disabled)
  - [ ] Sidebar updates (✓ appears)
- [ ] Navigation buttons
  - [ ] Previous button (disabled if first lesson)
  - [ ] Next button (disabled if last lesson)
  - [ ] Click → navigates to prev/next lesson
- [ ] Theme toggle
  - [ ] Click → switches dark/light
  - [ ] Persists across page loads
- [ ] Back to Season link works

### 6.4 Frontend Tests - Mobile

**Open on mobile or DevTools mobile view:**

- [ ] Hamburger menu visible (top-left)
- [ ] Click hamburger → sidebar slides in
- [ ] Backdrop darkens
- [ ] Click outside sidebar → closes
- [ ] Sidebar shows all lessons
- [ ] Layout stacks vertically
- [ ] Video responsive (16:9 ratio)
- [ ] Touch targets large enough
- [ ] Chat input expands on focus
- [ ] All buttons tappable
- [ ] Smooth scrolling

### 6.5 Edge Case Tests

1. **First lesson in season:**
   - [ ] Previous button disabled
   - [ ] Next button enabled

2. **Last lesson in season:**
   - [ ] Previous button enabled
   - [ ] Next button disabled

3. **Lesson with no video:**
   - [ ] Skool message displays
   - [ ] Link to Skool works

4. **Empty chat history:**
   - [ ] Shows "No messages yet" placeholder
   - [ ] Can send first message

5. **Very long AI response:**
   - [ ] Streams correctly
   - [ ] All text appears

6. **Network error during chat:**
   - [ ] Shows error message
   - [ ] Can retry

7. **Missing transcript:**
   - [ ] Transcript toggle disabled
   - [ ] "Coming soon" fallback for lesson content

8. **Already completed lesson:**
   - [ ] Mark complete button shows "Completed"
   - [ ] Button disabled
   - [ ] Sidebar shows ✓

9. **Invalid lesson ID:**
   - [ ] Shows "Lesson not found" error
   - [ ] Link back to dashboard

---

## 🎉 PHASE 7.3 COMPLETE!

**Phase 7.3 is DONE when ALL of the following are true:**

1. ✅ Database table created and tested
2. ✅ 4 backend routes working and verified
3. ✅ Lesson page renders with all components
4. ✅ Video OR Skool message displays correctly
5. ✅ AI lesson content generates (or shows fallback)
6. ✅ Transcript loads and toggles (when available)
7. ✅ Chat interface functional with persistence
8. ✅ Chat history loads on page reload
9. ✅ Mark complete updates database and UI
10. ✅ Navigation (prev/next/sidebar) works perfectly
11. ✅ Mobile experience smooth and beautiful
12. ✅ All desktop tests pass
13. ✅ All mobile tests pass
14. ✅ All edge cases handled gracefully
15. ✅ No console errors
16. ✅ Theme toggle works
17. ✅ Performance is good (<2s page load)

**User can now:**
- Navigate from Dashboard → Season → Lesson ✅
- Watch videos OR see Skool links ✅
- Read AI-generated lesson summaries ✅
- View transcripts (when available) ✅
- Chat with AI tutor about the lesson ✅
- Mark lessons complete ✅
- Navigate between lessons easily ✅
- Use on mobile devices ✅

---

## 📋 POST-IMPLEMENTATION CHECKLIST

After Replit Agent completes implementation:

### Verification Steps

1. **Database:**
   ```sql
   SELECT COUNT(*) FROM lesson_chats;
   ```

2. **Backend:**
   ```bash
   curl http://localhost:5000/api/lesson/4 | jq '.lesson.lesson_title'
   ```

3. **Frontend:**
   - Open `http://localhost:5000/lesson/4`
   - Check browser console (no errors)
   - Test one feature from each category above

4. **Mobile:**
   - Open DevTools responsive mode
   - Set to iPhone 12 (390x844)
   - Test hamburger menu
   - Test chat interface

### Bug Fixes

If you encounter issues:

1. **Console errors:** Check browser console, fix JavaScript errors
2. **API errors:** Check server logs, verify routes are registered
3. **Styling issues:** Verify CSS file is loaded, check data-theme attribute
4. **Database errors:** Verify table exists, check foreign keys

### Performance Optimization

- [ ] Check page load time (<2s)
- [ ] Test with slow 3G network
- [ ] Verify no memory leaks
- [ ] Check streaming performance

---

**End of Part 3 - PHASE 7.3 COMPLETE! 🎉**
