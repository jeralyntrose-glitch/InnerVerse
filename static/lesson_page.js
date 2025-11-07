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
    
    const pathParts = window.location.pathname.split('/');
    state.courseId = pathParts[2];
    state.lessonId = pathParts[3];
    
    if (!state.courseId || !state.lessonId) {
        showError('Invalid lesson URL');
        return;
    }
    
    await loadLessonData();
    setupEventListeners();
    hideLoading();
    
    console.log('✅ Lesson page initialized');
});

// ============================================================================
// DATA LOADING
// ============================================================================

async function loadLessonData() {
    try {
        showLoading();
        
        const courseResponse = await fetch(`${CONFIG.api.courses}/${state.courseId}`);
        const courseResult = await courseResponse.json();
        
        if (!courseResult.success) {
            throw new Error('Failed to load course');
        }
        
        state.course = courseResult.course;
        
        const lessonsResponse = await fetch(`${CONFIG.api.courses}/${state.courseId}/lessons`);
        const lessonsResult = await lessonsResponse.json();
        
        if (!lessonsResult.success) {
            throw new Error('Failed to load lessons');
        }
        
        state.allLessons = lessonsResult.lessons;
        state.lesson = state.allLessons.find(l => l.id === state.lessonId);
        state.currentLessonIndex = state.allLessons.findIndex(l => l.id === state.lessonId);
        
        if (!state.lesson) {
            throw new Error('Lesson not found');
        }
        
        await loadConcepts();
        renderLessonContent();
        loadNotes();
        
    } catch (error) {
        console.error('Error loading lesson:', error);
        showError(error.message);
    }
}

async function loadConcepts() {
    if (state.lesson.concept_ids && state.lesson.concept_ids.length > 0) {
        try {
            const conceptsPromises = state.lesson.concept_ids.map(id => 
                fetch(`${CONFIG.api.concepts}/${id}`).then(r => r.json())
            );
            const results = await Promise.all(conceptsPromises);
            state.concepts = results.filter(r => r.success).map(r => r.concept);
        } catch (error) {
            console.error('Error loading concepts:', error);
            state.concepts = [];
        }
    } else {
        state.concepts = [];
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

function renderConcepts() {
    const grid = document.getElementById('concepts-grid');
    
    if (state.concepts.length === 0) {
        grid.innerHTML = '<div class="loading-skeleton">No concepts assigned yet (Phase 6)</div>';
        return;
    }
    
    grid.innerHTML = state.concepts.map(concept => `
        <div class="concept-card" data-concept-id="${concept.id}" onclick="openConceptDetail('${concept.id}')">
            <div class="concept-title">${concept.name}</div>
            <div class="concept-description">${concept.description || 'Click to learn more'}</div>
        </div>
    `).join('');
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
        
        showToast('Lesson marked as complete!', 'success');
        
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
    
    try {
        setTimeout(() => {
            addChatMessage(
                `AI chat integration coming in Phase 5! For now, I can only say: That's a great question about "${state.lesson.title}"!`,
                'ai'
            );
        }, 500);
        
    } catch (error) {
        console.error('Chat error:', error);
        addChatMessage('Sorry, I encountered an error. Please try again.', 'ai');
    }
}

function addChatMessage(text, sender) {
    const messagesContainer = document.getElementById('chat-messages');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}-message`;
    
    const avatar = sender === 'ai' ? '🤖' : '👤';
    
    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            ${text}
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

window.LessonPage = { state, loadLessonData, renderLessonContent };
