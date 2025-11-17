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
        // RESET STATE for new lesson (Fix #4)
        state.isGeneratingLesson = false;
        state.isGeneratingChat = false;
        state.transcriptLoaded = false;
        
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
        
        // Show loading state with better messaging
        contentEl.innerHTML = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p style="margin-top: 16px; font-size: 16px; color: var(--text-secondary);">
                    🤖 Generating lesson content from transcript...
                </p>
                <p style="margin-top: 8px; font-size: 14px; color: var(--text-muted);">
                    This may take 10-20 seconds
                </p>
            </div>
        `;
        
        // Query backend API (server-side proxy keeps credentials secure)
        const response = await fetch(`${CONFIG.API_BASE}/api/lesson/${state.lessonId}/ai-chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: `Create a comprehensive lesson summary from the transcript with ID "${lesson.transcript_id}". 

Include:
- Key concepts and main teaching points
- Practical examples from the video
- Actionable insights
- Important quotes or memorable moments

Format with clear headers and organized sections. Make it educational and engaging.`,
                transcript_id: lesson.transcript_id
            })
        });
        
        if (!response.ok) {
            throw new Error(`Backend API error: ${response.status}`);
        }
        
        // Read streamed response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullResponse = '';
        let streamContainer = null;
        let hasStartedStreaming = false;
        
        // Parse SSE format: "data: {text}\n\n"
        let buffer = '';
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) break;
            
            // Decode chunk and add to buffer
            const chunk = decoder.decode(value, { stream: true });
            buffer += chunk;
            
            // Parse SSE events (split on double newlines)
            const events = buffer.split('\n\n');
            
            // Keep last incomplete event in buffer
            buffer = events.pop() || '';
            
            // Process complete events
            for (const event of events) {
                // Extract data from SSE format
                const lines = event.split('\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const text = line.substring(6); // Remove "data: " prefix
                        fullResponse += text;
                        
                        // Clear loading state ONLY when first chunk arrives
                        if (!hasStartedStreaming) {
                            contentEl.innerHTML = '<div class="streaming-content"></div>';
                            streamContainer = contentEl.querySelector('.streaming-content');
                            hasStartedStreaming = true;
                        }
                        
                        // Update UI in real-time with formatted markdown
                        if (streamContainer) {
                            streamContainer.innerHTML = formatMarkdown(fullResponse);
                            
                            // Auto-scroll to bottom as content streams in
                            contentEl.scrollTop = contentEl.scrollHeight;
                        }
                    }
                }
            }
        }
        
        // Parse and clean the final response
        fullResponse = parseAndCleanResponse(fullResponse);
        
        // Final format with cleaned response
        if (streamContainer) {
            streamContainer.innerHTML = formatMarkdown(fullResponse);
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
// RESPONSE PARSING AND CLEANING
// ==============================================================================

function parseAndCleanResponse(text) {
    if (!text) return '';
    
    // Try to parse JSON wrapper if present: {"answer":"..."}
    try {
        // Check if response starts with JSON object
        if (text.trim().startsWith('{')) {
            const parsed = JSON.parse(text);
            if (parsed.answer) {
                text = parsed.answer;
            }
        }
    } catch (e) {
        // Not JSON, use as-is
        console.log('Response is not JSON, using raw text');
    }
    
    // Unescape JSON string escapes (\", \\, etc)
    text = text
        .replace(/\\"/g, '"')      // \" → "
        .replace(/\\'/g, "'")      // \' → '
        .replace(/\\\\/g, '\\')    // \\ → \
        .replace(/\\n/g, '\n')     // \n → newline
        .replace(/\\t/g, '\t');    // \t → tab
    
    return text;
}

// ==============================================================================
// MARKDOWN FORMATTING
// ==============================================================================

function formatMarkdown(text) {
    if (!text) return '';
    
    // Text is already cleaned by parseAndCleanResponse
    // Just convert any remaining literal \n to actual newlines
    text = text.replace(/\\n/g, '\n');
    
    // HTML escape function (CRITICAL for XSS prevention)
    function escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
    
    // Process inline formatting (after HTML escaping)
    function processInline(line) {
        line = escapeHtml(line);  // ALWAYS escape first!
        // Bold
        line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        line = line.replace(/__(.+?)__/g, '<strong>$1</strong>');
        // Italic
        line = line.replace(/(?<!\*)\*([^*]+?)\*(?!\*)/g, '<em>$1</em>');
        line = line.replace(/(?<!_)_([^_]+?)_(?!_)/g, '<em>$1</em>');
        // Inline code
        line = line.replace(/`([^`]+)`/g, '<code>$1</code>');
        return line;
    }
    
    // Split into blocks by double newlines
    const blocks = text.split(/\n\n+/);
    const htmlBlocks = [];
    
    for (let block of blocks) {
        block = block.trim();
        if (!block) continue;
        
        const lines = block.split('\n');
        
        // Check for horizontal rule (---, ***, ___)
        if (block.match(/^[\-\*_]{3,}$/)) {
            htmlBlocks.push('<hr>');
            continue;
        }
        
        // Check for code block (triple backticks)
        if (block.startsWith('```') && block.endsWith('```')) {
            const code = escapeHtml(block.slice(3, -3).trim());
            htmlBlocks.push(`<pre><code>${code}</code></pre>`);
            continue;
        }
        
        // Check for header
        if (lines[0].startsWith('#')) {
            const headerMatch = lines[0].match(/^(#{1,3})\s+(.+)$/);
            if (headerMatch) {
                const level = headerMatch[1].length;
                const content = processInline(headerMatch[2]);
                const tag = level === 1 ? 'h3' : (level === 2 ? 'h3' : 'h4');
                htmlBlocks.push(`<${tag}>${content}</${tag}>`);
                continue;
            }
        }
        
        // Check for list (ANY line starts with list marker)
        const hasUnorderedMarker = lines.some(line => line.match(/^[\*\-]\s+/));
        const hasOrderedMarker = lines.some(line => line.match(/^\d+\.\s+/));
        
        if (hasUnorderedMarker || hasOrderedMarker) {
            const listItems = [];
            let currentItem = null;
            // Determine primary list type from FIRST marker (not whole block)
            const firstMarkerLine = lines.find(line => 
                line.match(/^[\*\-]\s+/) || line.match(/^\d+\.\s+/)
            );
            const isOrdered = firstMarkerLine && firstMarkerLine.match(/^\d+\.\s+/) !== null;
            
            for (const line of lines) {
                // Match primary marker type OR indented sub-bullets
                const orderedMatch = line.match(/^\d+\.\s+(.+)$/);
                const unorderedMatch = line.match(/^[\*\-]\s+(.+)$/);
                const indentedMatch = line.match(/^\s{2,}[\*\-]\s+(.+)$/);  // Indented bullets
                
                if (isOrdered && orderedMatch) {
                    // Top-level numbered item
                    if (currentItem) {
                        listItems.push(`<li>${currentItem}</li>`);
                    }
                    currentItem = processInline(orderedMatch[1]);
                } else if (!isOrdered && unorderedMatch) {
                    // Top-level bullet item
                    if (currentItem) {
                        listItems.push(`<li>${currentItem}</li>`);
                    }
                    currentItem = processInline(unorderedMatch[1]);
                } else if (indentedMatch && currentItem !== null) {
                    // Indented sub-bullet (treat as continuation with bullet)
                    currentItem += '<br>&nbsp;&nbsp;• ' + processInline(indentedMatch[1]);
                } else if (currentItem !== null && line.trim()) {
                    // Regular continuation line
                    currentItem += '<br>' + processInline(line.trim());
                }
            }
            
            // Add final item
            if (currentItem) {
                listItems.push(`<li>${currentItem}</li>`);
            }
            
            if (listItems.length > 0) {
                const tag = isOrdered ? 'ol' : 'ul';
                htmlBlocks.push(`<${tag}>${listItems.join('')}</${tag}>`);
                continue;
            }
        }
        
        // Regular paragraph - join lines and process inline
        const paragraph = lines.map(processInline).join('<br>');
        htmlBlocks.push(`<p>${paragraph}</p>`);
    }
    
    return htmlBlocks.join('\n');
}

// ==============================================================================
// TRANSCRIPT LOADING
// ==============================================================================

async function loadTranscript(transcriptId) {
    if (!state.lessonId) {
        console.log('⚠️ No lesson ID available');
        return;
    }
    
    try {
        console.log(`📄 Loading transcript for lesson ${state.lessonId}...`);
        
        // Use new direct transcript endpoint
        const response = await fetch(`${CONFIG.API_BASE}/api/lesson/${state.lessonId}/transcript`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (!data.available || !data.transcript) {
            console.log('⚠️ Transcript not available:', data.error || 'Unknown reason');
            // Keep button disabled
            return;
        }
        
        // Success! Display transcript
        const transcriptText = document.getElementById('transcriptText');
        const transcriptToggle = document.getElementById('transcriptToggle');
        
        if (transcriptText) {
            transcriptText.textContent = data.transcript;
            state.transcriptLoaded = true;
        }
        
        if (transcriptToggle) {
            transcriptToggle.disabled = false;
        }
        
        console.log('✅ Transcript loaded successfully');
        
    } catch (error) {
        console.error('❌ Error loading transcript:', error);
        // Transcript is optional, so just log the error
        // Button stays disabled
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
        
        // Format AI messages, escape user messages
        const formattedContent = msg.role === 'assistant' 
            ? formatAIChatMessage(msg.content)
            : escapeHtml(msg.content);
        
        return `
            <div class="message ${msg.role}-message">
                <div class="message-content">${formattedContent}</div>
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
        
        // Clear input IMMEDIATELY
        input.value = '';
        
        // Render IMMEDIATELY (optimistic UI!)
        renderChatHistory();
        
        // Save user message in background (don't await)
        saveChatMessage(userMessage).catch(err => {
            console.error('Failed to save user message:', err);
        });
        
        // Show typing indicator
        showTypingIndicator();
        
        // Get lesson context
        const lessonContext = state.lessonData?.lesson ? 
            `This question is about the lesson: "${state.lessonData.lesson.lesson_title}" (Season ${state.lessonData.lesson.season_number}).` : '';
        
        // Query backend (server-side proxy keeps credentials secure)
        const response = await fetch(`${CONFIG.API_BASE}/api/lesson/${state.lessonId}/ai-chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: `${lessonContext}\n\nUser question: ${message}`,
                transcript_id: state.lessonData?.lesson?.transcript_id || ''
            })
        });
        
        if (!response.ok) {
            throw new Error(`Backend API error: ${response.status}`);
        }
        
        // Stream AI response WORD-BY-WORD (like ChatGPT!)
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullResponse = '';
        let firstChunk = true;
        
        // Create AI message container (but keep dots visible!)
        const aiMessageId = createAIMessageContainer();
        
        // Stream chunks as they arrive (INSTANT UPDATES!)
        // Parse SSE format: "data: {text}\n\n"
        let buffer = '';
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) break;
            
            // Decode chunk and add to buffer
            const chunk = decoder.decode(value, { stream: true });
            buffer += chunk;
            
            // Parse SSE events (split on double newlines)
            const events = buffer.split('\n\n');
            
            // Keep last incomplete event in buffer
            buffer = events.pop() || '';
            
            // Process complete events
            for (const event of events) {
                // Extract data from SSE format
                const lines = event.split('\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const text = line.substring(6); // Remove "data: " prefix
                        
                        // Remove typing dots on FIRST non-empty chunk
                        if (firstChunk && text.trim()) {
                            removeTypingIndicator();
                            firstChunk = false;
                        }
                        
                        fullResponse += text;
                        
                        // Update message IMMEDIATELY with new text (streaming effect!)
                        updateAIMessage(aiMessageId, fullResponse);
                        
                        // Auto-scroll to show new content
                        scrollChatToBottom();
                    }
                }
            }
        }
        
        // Final cleanup - remove any JSON wrapper if present
        try {
            const parsed = JSON.parse(fullResponse);
            if (parsed.answer) {
                fullResponse = parsed.answer;
                updateAIMessage(aiMessageId, fullResponse);
            }
        } catch (e) {
            // Not JSON, that's fine - use raw text
        }
        
        // Save AI response to history
        const aiMessage = {
            role: 'assistant',
            content: fullResponse,
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
        // Format the content before displaying
        const formatted = formatAIChatMessage(content);
        contentEl.innerHTML = formatted;
        scrollChatToBottom();
    }
}

function formatAIChatMessage(text) {
    if (!text) return '';
    
    let formatted = text;
    
    // Convert literal \n to actual line breaks
    formatted = formatted.replace(/\\n/g, '\n');
    
    // Convert newlines to <br> tags
    formatted = formatted.replace(/\n/g, '<br>');
    
    // Bold text: **text** or __text__
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/__(.+?)__/g, '<strong>$1</strong>');
    
    // Italic text: *text* or _text_ (avoid conflicts with bold)
    formatted = formatted.replace(/(?<!\*)\*([^*]+?)\*(?!\*)/g, '<em>$1</em>');
    formatted = formatted.replace(/(?<!_)_([^_]+?)_(?!_)/g, '<em>$1</em>');
    
    // Inline code: `text`
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Bullet points: - or *
    formatted = formatted.replace(/^[\-\*] (.+)$/gm, '• $1');
    
    return formatted;
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
    
    // Check current state and toggle it
    const isCompleted = btn.classList.contains('completed');
    const newState = !isCompleted;
    
    try {
        // Update backend with new state
        const response = await fetch(`${CONFIG.API_BASE}/api/lesson/${state.lessonId}/complete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                completed: newState
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        console.log(`✅ Lesson marked ${newState ? 'complete' : 'incomplete'}`);
        
        // Update UI
        updateMarkCompleteButton(newState);
        
        // Update sidebar
        if (state.lessonData) {
            const lessonInSidebar = state.lessonData.season_lessons.find(l => l.lesson_id === state.lessonId);
            if (lessonInSidebar) {
                lessonInSidebar.completed = newState;
                renderSidebar(state.lessonData.season_lessons, state.lessonId);
            }
        }
        
    } catch (error) {
        console.error('❌ Error toggling lesson completion:', error);
        alert('Failed to update lesson status. Please try again.');
    }
}

function updateMarkCompleteButton(completed) {
    const btn = document.getElementById('markCompleteBtn');
    if (!btn) return;
    
    if (completed) {
        btn.classList.add('completed');
        btn.querySelector('.btn-text').textContent = 'Completed ✓';
        btn.title = 'Click to mark as incomplete';
    } else {
        btn.classList.remove('completed');
        btn.querySelector('.btn-text').textContent = 'Mark as Complete';
        btn.title = 'Click to mark this lesson as complete';
    }
    
    // ALWAYS keep it clickable (never disable)
    btn.disabled = false;
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
