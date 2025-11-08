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

// =============================================================================
// FEATURE FLAG: PWA BACKGROUND PROCESSING
// =============================================================================
const ENABLE_BACKGROUND_PROCESSING = false; // OFF - Stable, working version
console.log(`🚦 [Lesson] Background processing: ${ENABLE_BACKGROUND_PROCESSING ? 'ENABLED' : 'DISABLED (using synchronous chat)'}`);

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
    loadConcepts().then(() => {
        console.log('✅ Concepts loaded, re-rendering...');
        renderConcepts(); // Re-render concepts section after they load
    });
    console.log('✅ Concepts loading in background');
    
    console.log('📝 Loading notes...');
    loadNotes();
    console.log('✅ Notes loaded');
}

async function loadConcepts() {
    const conceptsUrl = `${CONFIG.api.lessons}/${state.lessonId}/concepts`;
    console.log('🌐 Concepts URL:', conceptsUrl);
    
    // Use XMLHttpRequest as fallback to bypass potential fetch interceptors
    return new Promise((resolve) => {
        const xhr = new XMLHttpRequest();
        
        xhr.timeout = 3000; // 3 second timeout
        xhr.ontimeout = () => {
            console.error('❌ XHR timeout after 3s');
            state.concepts = [];
            resolve();
        };
        
        xhr.onerror = (error) => {
            console.error('❌ XHR error:', error);
            state.concepts = [];
            resolve();
        };
        
        xhr.onload = () => {
            console.log('✅ XHR complete, status:', xhr.status);
            try {
                if (xhr.status === 200) {
                    const result = JSON.parse(xhr.responseText);
                    console.log('✅ JSON parsed, success:', result.success);
                    
                    if (result.success) {
                        state.concepts = result.concepts || [];
                        console.log(`✅ Loaded ${state.concepts.length} assigned concepts`);
                    } else {
                        console.warn('❌ API returned success=false');
                        state.concepts = [];
                    }
                } else {
                    console.error('❌ Bad status:', xhr.status);
                    state.concepts = [];
                }
            } catch (error) {
                console.error('❌ Parse error:', error);
                state.concepts = [];
            }
            resolve();
        };
        
        console.log('📡 Starting XHR request...');
        xhr.open('GET', conceptsUrl);
        xhr.setRequestHeader('Accept', 'application/json');
        xhr.send();
    });
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
    
    // Header with count
    const header = `<div class="concepts-header">📚 Related Concepts (${state.concepts.length})</div>`;
    
    // Confidence colors and emojis
    const confidenceStyles = {
        'high': { bg: '#dcfce7', border: '#86efac', emoji: '🎯' },
        'medium': { bg: '#fef9c3', border: '#fde047', emoji: '✓' },
        'low': { bg: '#f3f4f6', border: '#d1d5db', emoji: '○' }
    };
    
    // Generate concept cards
    const cards = state.concepts.map((concept, index) => {
        const style = confidenceStyles[concept.confidence] || confidenceStyles.low;
        const truncatedDesc = concept.description?.substring(0, 120) || 'No description available';
        const hasMore = (concept.description || '').length > 120;
        
        return `
            <div class="concept-card" 
                 data-concept-id="${concept.id}"
                 data-expanded="false"
                 style="background: ${style.bg}; border: 2px solid ${style.border};">
                <div class="concept-card-header">
                    <div class="concept-title-row">
                        <span class="concept-emoji">${style.emoji}</span>
                        <span class="concept-name">${concept.name}</span>
                    </div>
                    <button class="concept-toggle-btn" 
                            onclick="toggleConcept('${concept.id}', event)"
                            aria-label="Toggle concept details">
                        ▼
                    </button>
                </div>
                <div class="concept-description concept-collapsed">
                    <div class="concept-short">
                        ${truncatedDesc}${hasMore ? '...' : ''}
                    </div>
                    <div class="concept-full" style="display: none;">
                        ${concept.description || 'No description available'}
                        <div class="concept-meta">
                            <span class="meta-item">
                                📊 Match: ${Math.round(concept.similarity_score * 100)}%
                            </span>
                            <span class="meta-item confidence-badge">
                                ${style.emoji} ${concept.confidence.toUpperCase()}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    grid.innerHTML = header + '<div class="concepts-grid-container">' + cards + '</div>';
}

function toggleConcept(conceptId, event) {
    event?.stopPropagation();
    
    const card = document.querySelector(`[data-concept-id="${conceptId}"]`);
    if (!card) return;
    
    const isExpanded = card.getAttribute('data-expanded') === 'true';
    const toggleBtn = card.querySelector('.concept-toggle-btn');
    const shortDesc = card.querySelector('.concept-short');
    const fullDesc = card.querySelector('.concept-full');
    
    if (isExpanded) {
        // Collapse
        card.setAttribute('data-expanded', 'false');
        toggleBtn.textContent = '▼';
        shortDesc.style.display = 'block';
        fullDesc.style.display = 'none';
    } else {
        // Expand
        card.setAttribute('data-expanded', 'true');
        toggleBtn.textContent = '▲';
        shortDesc.style.display = 'none';
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
    
    let notesTimeout;
    document.getElementById('lesson-notes').addEventListener('input', () => {
        clearTimeout(notesTimeout);
        notesTimeout = setTimeout(saveNotes, 1000);
    });
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

// ============================================================================
// BACKGROUND PROCESSING INITIALIZATION (PWA)
// ============================================================================

let backgroundManager = null;
if (ENABLE_BACKGROUND_PROCESSING) {
    console.log('🚀 [Lesson] Initializing BackgroundMessageManager');
    backgroundManager = new BackgroundMessageManager();
    
    // Initialize and check for pending jobs on page load
    (async () => {
        await backgroundManager.ready;
        console.log('✅ [Lesson] BackgroundMessageManager ready');
        
        // Check for pending jobs immediately on page load
        // Note: Lesson chat needs a background endpoint to fully support this
        await backgroundManager.checkPendingJobsOnResume(null, state.lessonId, (response) => {
            if (response) {
                addChatMessage(response, 'ai');
            }
        });
    })();
    
    // Resume detection: Check for pending jobs when app comes back to foreground
    document.addEventListener('visibilitychange', async () => {
        if (!document.hidden && backgroundManager) {
            console.log('👀 [Lesson] App visible - checking for pending messages');
            await backgroundManager.checkPendingJobsOnResume(null, state.lessonId, (response) => {
                if (response) {
                    addChatMessage(response, 'ai');
                }
            });
        }
    });
    
    // Also check on focus (for iOS)
    window.addEventListener('focus', async () => {
        if (backgroundManager) {
            console.log('🔍 [Lesson] Window focused - checking for pending messages');
            await backgroundManager.checkPendingJobsOnResume(null, state.lessonId, (response) => {
                if (response) {
                    addChatMessage(response, 'ai');
                }
            });
        }
    });
    
    console.log('✅ [Lesson] Background processing listeners registered');
}

window.LessonPage = { state, loadLessonData, renderLessonContent };
