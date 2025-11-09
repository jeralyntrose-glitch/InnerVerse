/**
 * InnerVerse Lesson Page
 * ======================
 * Split-screen learning interface with AI chat
 */

// ============================================================================
// CONFIGURATION
// ============================================================================

const CONFIG = {
    api: {
        courses: '/api/courses',
        lessons: '/api/lessons',
        concepts: '/api/concepts',
        progress: '/api/courses'
    }
};

// ============================================================================
// STATE
// ============================================================================

const state = {
    courseId: null,
    lessonId: null,
    course: null,
    lesson: null,
    allLessons: [],
    concepts: [],
    currentLessonIndex: 0
};

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🎓 Initializing lesson page...');
    
    showLoading();
    
    try {
        const pathParts = window.location.pathname.split('/');
        state.courseId = pathParts[2];
        state.lessonId = pathParts[3];
        
        console.log('📍 Course ID:', state.courseId);
        console.log('📍 Lesson ID:', state.lessonId);
        
        if (!state.courseId || !state.lessonId) {
            console.error('❌ Invalid URL - missing course/lesson ID');
            showError('Invalid lesson URL');
            return;
        }
        
        console.log('⏳ Loading lesson data...');
        await loadLessonData();
        console.log('✅ Lesson data loaded');
        
        console.log('⏳ Setting up event listeners...');
        setupEventListeners();
        console.log('✅ Event listeners set up');
        
        console.log('✅ Lesson page initialized successfully');
    } catch (error) {
        console.error('❌ Error loading lesson:', error);
        console.error('❌ Error stack:', error.stack);
        showError(error.message);
    } finally {
        console.log('🔄 Hiding loading overlay...');
        hideLoading();
        console.log('✅ Loading overlay hidden');
    }
});

// ============================================================================
// DATA LOADING
// ============================================================================

async function loadLessonData() {
    console.log('📡 Fetching course data...');
    const courseResponse = await fetch(`${CONFIG.api.courses}/${state.courseId}`);
    console.log('✅ Course response received');
    const courseResult = await courseResponse.json();
    
    if (!courseResult.success) {
        throw new Error('Failed to load course');
    }
    
    state.course = courseResult.course;
    console.log('✅ Course data stored');
    
    console.log('📡 Fetching lessons data...');
    const lessonsResponse = await fetch(`${CONFIG.api.courses}/${state.courseId}/lessons`);
    console.log('✅ Lessons response received');
    const lessonsResult = await lessonsResponse.json();
    
    if (!lessonsResult.success) {
        throw new Error('Failed to load lessons');
    }
    
    state.allLessons = lessonsResult.lessons;
    state.lesson = state.allLessons.find(l => l.id === state.lessonId);
    state.currentLessonIndex = state.allLessons.findIndex(l => l.id === state.lessonId);
    console.log('✅ Found lesson at index', state.currentLessonIndex);
    
    if (!state.lesson) {
        throw new Error('Lesson not found');
    }
    
    console.log('🎨 Rendering lesson content (concepts will load async)...');
    renderLessonContent();
    console.log('✅ Lesson content rendered');
    
    console.log('📡 Loading concepts asynchronously...');
    loadConcepts()
        .then(() => {
            console.log('✅ [MAIN] loadConcepts() promise resolved');
            console.log('✅ [MAIN] state.concepts after load:', state.concepts);
            console.log('✅ [MAIN] Re-rendering concepts...');
            renderConcepts();
            console.log('✅ [MAIN] Concepts re-rendered');
        })
        .catch((error) => {
            console.error('🔴 [MAIN] loadConcepts() promise rejected:', error);
            console.error('🔴 [MAIN] Error stack:', error.stack);
        });
    console.log('✅ Concepts loading in background');
    
    console.log('📝 Loading notes...');
    loadNotes();
    console.log('✅ Notes loaded');
}

async function loadConcepts() {
    console.log('🔵 [CONCEPTS] ========== START loadConcepts() ==========');
    const conceptsUrl = `${CONFIG.api.lessons}/${state.lessonId}/concepts`;
    console.log('🔵 [CONCEPTS] URL:', conceptsUrl);
    console.log('🔵 [CONCEPTS] Lesson ID:', state.lessonId);
    console.log('🔵 [CONCEPTS] Current concepts array:', state.concepts);
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
        console.error('🔴 [CONCEPTS] TIMEOUT - Aborting fetch after 5 seconds');
        controller.abort();
    }, 5000);
    
    try {
        console.log('🔵 [CONCEPTS] Starting fetch request with 5s timeout...');
        const startTime = Date.now();
        
        const response = await fetch(conceptsUrl, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            },
            cache: 'no-cache',
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        const fetchTime = Date.now() - startTime;
        console.log(`🔵 [CONCEPTS] Fetch completed in ${fetchTime}ms`);
        console.log('🔵 [CONCEPTS] Response status:', response.status);
        console.log('🔵 [CONCEPTS] Response ok:', response.ok);
        console.log('🔵 [CONCEPTS] Response headers:', [...response.headers.entries()]);
        
        if (!response.ok) {
            console.error('🔴 [CONCEPTS] Bad response status:', response.status);
            state.concepts = [];
            return;
        }
        
        console.log('🔵 [CONCEPTS] Parsing JSON...');
        const result = await response.json();
        console.log('🔵 [CONCEPTS] JSON parsed successfully:', result);
        console.log('🔵 [CONCEPTS] Result type:', typeof result);
        console.log('🔵 [CONCEPTS] Result.success:', result.success);
        console.log('🔵 [CONCEPTS] Result.concepts:', result.concepts);
        console.log('🔵 [CONCEPTS] Result.concepts length:', result.concepts?.length);
        
        if (result.success && result.concepts) {
            state.concepts = result.concepts;
            console.log(`✅ [CONCEPTS] Successfully loaded ${state.concepts.length} concepts`);
            console.log('✅ [CONCEPTS] State updated, concepts:', state.concepts);
        } else {
            console.warn('⚠️ [CONCEPTS] API returned success=false or no concepts');
            state.concepts = [];
        }
        
    } catch (error) {
        clearTimeout(timeoutId);
        
        if (error.name === 'AbortError') {
            console.error('🔴 [CONCEPTS] FETCH ABORTED due to timeout');
        } else {
            console.error('🔴 [CONCEPTS] EXCEPTION CAUGHT:', error);
            console.error('🔴 [CONCEPTS] Error name:', error.name);
            console.error('🔴 [CONCEPTS] Error message:', error.message);
            console.error('🔴 [CONCEPTS] Error stack:', error.stack);
        }
        state.concepts = [];
    } finally {
        console.log('🔵 [CONCEPTS] ========== END loadConcepts() ==========');
        console.log('🔵 [CONCEPTS] Final state.concepts:', state.concepts);
        console.log('🔵 [CONCEPTS] Final state.concepts.length:', state.concepts.length);
    }
}

// ============================================================================
// RENDERING
// ============================================================================

function renderLessonContent() {
    document.getElementById('course-title').textContent = state.course.title;
    document.getElementById('lesson-title').textContent = state.lesson.title;
    
    document.getElementById('lesson-title-main').textContent = state.lesson.title;
    document.getElementById('lesson-duration').textContent = `${state.lesson.estimated_minutes || 30} min`;
    document.getElementById('lesson-difficulty').textContent = state.lesson.difficulty || 'foundational';
    document.getElementById('lesson-description').textContent = state.lesson.description || 'No description available';
    
    document.getElementById('lesson-number').textContent = 
        `Lesson ${state.currentLessonIndex + 1} of ${state.allLessons.length}`;
    
    updateLessonStatus();
    renderConcepts();
    updateNavigationButtons();
    updateProgressBar();
    
    if (state.lesson.lesson_content) {
        showLessonContent(state.lesson.lesson_content);
    }
    
    if (state.lesson.video_references && state.lesson.video_references.length > 0) {
        showVideo(state.lesson.video_references[0].url);
    }
    
    if (state.lesson.document_references && state.lesson.document_references.length > 0) {
        const transcriptDoc = state.lesson.document_references.find(d => d.title.includes('transcript'));
        if (transcriptDoc) {
            showTranscript('Transcript available for this lesson.');
        }
    }
}

function showLessonContent(content) {
    const contentSection = document.getElementById('lesson-content-section');
    const contentBody = document.getElementById('lesson-content-body');
    
    contentBody.innerHTML = content;
    contentSection.style.display = 'block';
}

function updateLessonStatus() {
    const statusEl = document.getElementById('lesson-status');
    const completedIds = state.course.completed_lesson_ids || [];
    const isCompleted = completedIds.includes(state.lessonId);
    
    if (isCompleted) {
        statusEl.textContent = '✓ Completed';
        statusEl.style.color = '#10b981';
    } else {
        statusEl.textContent = '● Not Started';
        statusEl.style.color = '#64748b';
    }
}

function renderConcepts() {
    const grid = document.getElementById('concepts-grid');
    
    if (state.concepts.length === 0) {
        grid.innerHTML = '<div class="empty-state">📚 No concepts assigned yet</div>';
        return;
    }
    
    // Confidence emojis
    const confidenceEmojis = {
        'high': '🎯',
        'medium': '✓',
        'low': '○'
    };
    
    // Generate compact concept cards for sidebar
    const cards = state.concepts.map((concept, index) => {
        const emoji = confidenceEmojis[concept.confidence] || confidenceEmojis.low;
        
        return `
            <div class="concept-card" 
                 data-concept-id="${concept.id}"
                 data-confidence="${concept.confidence}"
                 data-expanded="false"
                 onclick="toggleConceptCard(event, '${concept.id}')">
                <div class="concept-card-header">
                    <div class="concept-title-row">
                        <span class="concept-emoji">${emoji}</span>
                        <span class="concept-name">${concept.name}</span>
                    </div>
                    <span class="concept-toggle-btn">▼</span>
                </div>
                <div class="concept-full" style="display: none;">
                    <div class="concept-description">
                        ${concept.description || 'No description available'}
                    </div>
                    <div class="concept-meta">
                        <span class="meta-item">
                            📊 ${Math.round(concept.similarity_score * 100)}%
                        </span>
                        <span class="meta-item">
                            📁 ${concept.category || 'General'}
                        </span>
                        <span class="confidence-badge ${concept.confidence}">
                            ${concept.confidence}
                        </span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    grid.innerHTML = cards;
}

// Toggle concept card expansion (Phase 6.5)
function toggleConceptCard(event, conceptId) {
    event?.stopPropagation();
    
    const card = document.querySelector(`[data-concept-id="${conceptId}"]`);
    if (!card) return;
    
    const isExpanded = card.getAttribute('data-expanded') === 'true';
    const fullDesc = card.querySelector('.concept-full');
    
    if (isExpanded) {
        // Collapse
        card.setAttribute('data-expanded', 'false');
        fullDesc.style.display = 'none';
    } else {
        // Expand
        card.setAttribute('data-expanded', 'true');
        fullDesc.style.display = 'block';
    }
}

function showVideo(url) {
    const videoSection = document.getElementById('video-section');
    const videoIframe = document.getElementById('video-iframe');
    
    const youtubeId = extractYouTubeId(url);
    if (youtubeId) {
        videoIframe.src = `https://www.youtube.com/embed/${youtubeId}`;
        videoSection.style.display = 'block';
    }
}

function showTranscript(text) {
    const transcriptSection = document.getElementById('transcript-section');
    const transcriptContent = document.getElementById('transcript-content');
    
    transcriptContent.textContent = text;
    transcriptSection.style.display = 'block';
}

function updateNavigationButtons() {
    const prevBtn = document.getElementById('prev-lesson-btn');
    const nextBtn = document.getElementById('next-lesson-btn');
    
    prevBtn.disabled = state.currentLessonIndex === 0;
    nextBtn.disabled = state.currentLessonIndex === state.allLessons.length - 1;
}

function updateProgressBar() {
    const completed = state.course.completed_lesson_ids?.length || 0;
    const total = state.allLessons.length;
    const percentage = (completed / total) * 100;
    
    document.getElementById('lesson-progress-fill').style.width = `${percentage}%`;
}

// ============================================================================
// EVENT LISTENERS
// ============================================================================

function setupEventListeners() {
    document.getElementById('back-btn').addEventListener('click', () => {
        window.location.href = '/learning-paths';
    });
    
    document.getElementById('prev-lesson-btn').addEventListener('click', () => {
        navigateLesson(-1);
    });
    
    document.getElementById('next-lesson-btn').addEventListener('click', () => {
        navigateLesson(1);
    });
    
    document.getElementById('mark-complete-btn').addEventListener('click', markComplete);
    
    document.getElementById('send-btn').addEventListener('click', sendChatMessage);
    
    document.getElementById('chat-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
    
    document.getElementById('switch-to-regular').addEventListener('click', () => {
        showToast('Regular chat mode coming in Phase 5!', 'info');
    });
    
    document.getElementById('delete-lesson-btn').addEventListener('click', handleDeleteLesson);
    
    // Sidebar toggle (Phase 6.5)
    document.getElementById('sidebar-toggle').addEventListener('click', toggleSidebar);
    
    let notesTimeout;
    document.getElementById('lesson-notes').addEventListener('input', () => {
        clearTimeout(notesTimeout);
        notesTimeout = setTimeout(saveNotes, 1000);
    });
}

// Toggle sidebar collapse (Phase 6.5)
function toggleSidebar() {
    const sidebar = document.getElementById('concepts-sidebar');
    sidebar.classList.toggle('collapsed');
}

async function markComplete() {
    try {
        const response = await fetch(`${CONFIG.api.progress}/${state.courseId}/lessons/${state.lessonId}/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: 'jeralyn' })
        });
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error('Failed to mark complete');
        }
        
        if (!state.course.completed_lesson_ids) {
            state.course.completed_lesson_ids = [];
        }
        if (!state.course.completed_lesson_ids.includes(state.lessonId)) {
            state.course.completed_lesson_ids.push(state.lessonId);
        }
        
        showToast('Lesson marked as complete!', 'success');
        
        updateLessonStatus();
        updateProgressBar();
        
        if (state.currentLessonIndex < state.allLessons.length - 1) {
            setTimeout(() => navigateLesson(1), 1500);
        }
        
    } catch (error) {
        console.error('Error marking complete:', error);
        showToast('Failed to mark complete', 'error');
    }
}

function navigateLesson(direction) {
    const newIndex = state.currentLessonIndex + direction;
    
    if (newIndex < 0 || newIndex >= state.allLessons.length) {
        return;
    }
    
    const nextLesson = state.allLessons[newIndex];
    window.location.href = `/learning-paths/${state.courseId}/${nextLesson.id}`;
}

// Delete lesson with 2-step confirmation (Phase 6.5)
async function handleDeleteLesson() {
    const lessonTitle = state.lesson.title || 'this lesson';
    
    // First confirmation
    const confirm1 = confirm(
        `⚠️ Delete this lesson?\n\n"${lessonTitle}"\n\nThis will remove all concept assignments.`
    );
    
    if (!confirm1) return;
    
    // Second confirmation
    const confirm2 = confirm('🚨 Are you SURE? This cannot be undone!');
    
    if (!confirm2) return;
    
    try {
        showLoading();
        
        const response = await fetch(`/api/lessons/${state.lessonId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✅ ' + data.message);
            window.location.href = '/learning-paths';
        } else {
            alert('❌ Error: ' + data.error);
        }
    } catch (error) {
        alert('❌ Failed to delete: ' + error.message);
    } finally {
        hideLoading();
    }
}

// ============================================================================
// CHAT FUNCTIONS
// ============================================================================

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    addChatMessage(message, 'user');
    input.value = '';
    
    const typingId = addTypingIndicator();
    
    try {
        const response = await fetch('/api/chat/lesson', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                course_id: state.courseId,
                lesson_id: state.lessonId,
                message: message
            })
        });
        
        const result = await response.json();
        
        removeTypingIndicator(typingId);
        
        if (!result.success) {
            throw new Error(result.error || 'Chat failed');
        }
        
        addChatMessage(result.message, 'ai');
        
        if (result.tokens) {
            console.log('💰 Token usage:', result.tokens);
            console.log('💵 Cost: $' + result.cost);
        }
        
    } catch (error) {
        console.error('Chat error:', error);
        removeTypingIndicator(typingId);
        addChatMessage('Sorry, I encountered an error. Please try again.', 'ai');
    }
}

function addTypingIndicator() {
    const messagesContainer = document.getElementById('chat-messages');
    const typingId = 'typing-' + Date.now();
    
    const typingDiv = document.createElement('div');
    typingDiv.id = typingId;
    typingDiv.className = 'chat-message ai-message';
    typingDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    
    messagesContainer.appendChild(typingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return typingId;
}

function removeTypingIndicator(typingId) {
    const typingDiv = document.getElementById(typingId);
    if (typingDiv) {
        typingDiv.remove();
    }
}

function addChatMessage(text, sender) {
    const messagesContainer = document.getElementById('chat-messages');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}-message`;
    
    const avatar = sender === 'ai' ? '🤖' : '👤';
    
    // Render markdown for AI messages, plain text for user messages
    let content;
    if (sender === 'ai') {
        // Render markdown and sanitize with DOMPurify
        const rawHtml = marked.parse(text);
        content = DOMPurify.sanitize(rawHtml);
    } else {
        // Escape HTML for user messages
        content = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
    
    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            ${content}
        </div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// ============================================================================
// NOTES
// ============================================================================

function saveNotes() {
    const notes = document.getElementById('lesson-notes').value;
    
    localStorage.setItem(`lesson_notes_${state.lessonId}`, notes);
    
    document.getElementById('notes-status').innerHTML = '✓ Notes saved';
}

function loadNotes() {
    const saved = localStorage.getItem(`lesson_notes_${state.lessonId}`);
    if (saved) {
        document.getElementById('lesson-notes').value = saved;
    }
}

// ============================================================================
// UTILITIES
// ============================================================================

function extractYouTubeId(url) {
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
    const match = url.match(regExp);
    return (match && match[2].length === 11) ? match[2] : null;
}

function openConceptDetail(conceptId) {
    showToast('Concept details coming in Phase 6!', 'info');
}

window.testConceptsFetch = async function() {
    console.log('🧪 [TEST] Manual concepts fetch test started');
    console.log('🧪 [TEST] Current lesson ID:', state.lessonId);
    console.log('🧪 [TEST] Calling loadConcepts()...');
    
    await loadConcepts();
    
    console.log('🧪 [TEST] loadConcepts() completed');
    console.log('🧪 [TEST] state.concepts:', state.concepts);
    console.log('🧪 [TEST] Calling renderConcepts()...');
    
    renderConcepts();
    
    console.log('🧪 [TEST] Test complete! Check the concepts grid on the page.');
    return state.concepts;
};

function showLoading() {
    document.getElementById('loading-overlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

function showError(message) {
    hideLoading();
    alert('Error: ' + message);
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => toast.remove(), 3000);
}

window.LessonPage = { state, loadLessonData, renderLessonContent };
