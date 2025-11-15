// ==============================================================================
// PHASE 7.2: SEASON VIEW JAVASCRIPT
// ==============================================================================

class SeasonView {
    constructor() {
        this.seasonNumber = null;
        this.seasonData = null;
        this.theme = localStorage.getItem('theme') || 'dark';
        
        this.init();
    }

    async init() {
        // Get season number from URL
        this.seasonNumber = this.getSeasonNumberFromURL();
        
        if (!this.seasonNumber) {
            this.showError('Invalid season URL');
            return;
        }

        // Set initial theme
        this.applyTheme();
        this.setupEventListeners();
        
        // Load season data
        await this.loadSeasonData();
    }

    // =========================================================================
    // URL PARSING
    // =========================================================================
    
    getSeasonNumberFromURL() {
        // URL format: /season/1 or /season/16
        const path = window.location.pathname;
        const match = path.match(/\/season\/([^\/]+)/);
        return match ? match[1] : null;
    }

    // =========================================================================
    // THEME MANAGEMENT
    // =========================================================================
    
    applyTheme() {
        document.body.setAttribute('data-theme', this.theme);
        const icon = this.theme === 'dark' ? '🌙' : '☀️';
        const themeIcon = document.querySelector('.theme-icon');
        if (themeIcon) {
            themeIcon.textContent = icon;
        }
    }

    toggleTheme() {
        this.theme = this.theme === 'dark' ? 'light' : 'dark';
        localStorage.setItem('theme', this.theme);
        this.applyTheme();
    }

    // =========================================================================
    // EVENT LISTENERS
    // =========================================================================
    
    setupEventListeners() {
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }
    }

    // =========================================================================
    // DATA LOADING
    // =========================================================================
    
    async loadSeasonData() {
        try {
            const response = await fetch(`/api/season/${this.seasonNumber}`);
            
            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('Season not found');
                }
                throw new Error('Failed to load season data');
            }

            this.seasonData = await response.json();

            // Render everything
            this.renderSeasonHero();
            this.renderLessonsList();

        } catch (error) {
            console.error('Error loading season:', error);
            this.showError(error.message || 'Failed to load season. Please try again.');
        }
    }

    // =========================================================================
    // RENDERING
    // =========================================================================
    
    renderSeasonHero() {
        const heroSection = document.getElementById('seasonHero');
        if (!heroSection || !this.seasonData) return;

        const season_info = this.seasonData.season_info;
        const progress_percent = season_info.progress_percent || 0;

        heroSection.innerHTML = `
            <nav class="breadcrumb">
                <a href="/" class="breadcrumb-link">Dashboard</a>
                <span class="breadcrumb-separator">›</span>
                <span>Module ${season_info.module_number}: ${season_info.module_name}</span>
                <span class="breadcrumb-separator">›</span>
                <span>Season ${season_info.season_number}</span>
            </nav>

            <div class="season-title-section">
                <div class="season-number">Season ${season_info.season_number}</div>
                <h1 class="season-title">${season_info.season_name}</h1>
                <span class="module-badge">
                    Module ${season_info.module_number}: ${season_info.module_name}
                </span>
            </div>

            <div class="season-stats">
                <div class="stat-item">
                    <span class="stat-label">Progress</span>
                    <span class="stat-value">
                        ${season_info.completed_lessons}/${season_info.total_lessons}
                    </span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Completion</span>
                    <span class="stat-value">${progress_percent}%</span>
                </div>
            </div>

            <div class="progress-bar-container">
                <div class="progress-bar" style="width: ${progress_percent}%"></div>
            </div>
        `;

        // Animate progress bar
        setTimeout(() => {
            const progressBar = heroSection.querySelector('.progress-bar');
            if (progressBar) {
                progressBar.style.width = `${progress_percent}%`;
            }
        }, 100);
    }

    renderLessonsList() {
        const container = document.getElementById('lessonsContainer');
        if (!container || !this.seasonData) return;

        const lessons = this.seasonData.lessons;

        // Clear loading state
        container.innerHTML = '';

        if (lessons.length === 0) {
            container.innerHTML = `
                <div class="loading-state">
                    <p>No lessons found in this season.</p>
                </div>
            `;
            return;
        }

        // Render each lesson
        lessons.forEach(lesson => {
            const lessonCard = this.createLessonCard(lesson);
            container.appendChild(lessonCard);
        });
    }

    createLessonCard(lesson) {
        const card = document.createElement('div');
        card.className = 'lesson-card';
        card.dataset.lessonId = lesson.lesson_id;

        // Determine status icon
        let statusIcon = '□'; // Not started
        let statusClass = 'not-started';
        
        if (lesson.completed) {
            statusIcon = '✓';
            statusClass = 'completed';
        } else if (lesson.last_accessed) {
            statusIcon = '▶';
            statusClass = 'in-progress';
        }

        // Format last accessed
        let accessedText = '';
        if (lesson.last_accessed) {
            const date = new Date(lesson.last_accessed);
            const now = new Date();
            const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
            
            if (diffDays === 0) {
                accessedText = 'Today';
            } else if (diffDays === 1) {
                accessedText = 'Yesterday';
            } else if (diffDays < 7) {
                accessedText = `${diffDays} days ago`;
            } else {
                accessedText = date.toLocaleDateString('en-US', { 
                    month: 'short', 
                    day: 'numeric' 
                });
            }
        }

        card.innerHTML = `
            <div class="lesson-status-icon ${statusClass}">
                ${statusIcon}
            </div>
            
            <div class="lesson-content">
                <div class="lesson-header">
                    <span class="lesson-number">Lesson ${lesson.lesson_number}</span>
                    <h3 class="lesson-title">${lesson.lesson_title}</h3>
                    ${lesson.has_video ? '<span class="video-badge">📹 Video</span>' : ''}
                </div>
                
                <div class="lesson-meta">
                    ${lesson.duration ? `
                        <div class="lesson-duration">
                            <span>⏱️</span>
                            <span>${lesson.duration}</span>
                        </div>
                    ` : ''}
                    
                    ${accessedText ? `
                        <div class="lesson-accessed">
                            <span>👁️</span>
                            <span>${accessedText}</span>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;

        // Click handler - navigate to lesson page (Phase 7.3)
        card.addEventListener('click', () => {
            this.onLessonClick(lesson.lesson_id);
        });

        return card;
    }

    // =========================================================================
    // EVENT HANDLERS
    // =========================================================================
    
    onLessonClick(lessonId) {
        // Navigate to lesson page (Phase 7.3 - will be built next)
        // For now, just log and show alert
        console.log('Navigate to lesson:', lessonId);
        
        // TODO: Replace with actual navigation in Phase 7.3
        alert(`Lesson page not yet implemented (Phase 7.3).\n\nLesson ID: ${lessonId}\n\nThis will navigate to the lesson page with video, AI content, and chat.`);
        
        // FUTURE (Phase 7.3):
        // window.location.href = `/lesson/${lessonId}`;
    }

    // =========================================================================
    // ERROR HANDLING
    // =========================================================================
    
    showError(message) {
        const heroSection = document.getElementById('seasonHero');
        const lessonsContainer = document.getElementById('lessonsContainer');
        
        if (heroSection) {
            heroSection.innerHTML = `
                <div style="text-align: center; padding: 40px; color: var(--text-secondary);">
                    <p style="font-size: 18px; margin-bottom: 16px;">⚠️ ${message}</p>
                    <a href="/" style="
                        display: inline-block;
                        background: var(--accent-primary);
                        color: white;
                        border: none;
                        padding: 12px 24px;
                        border-radius: 8px;
                        text-decoration: none;
                        font-size: 16px;
                        font-weight: 600;
                    ">
                        ← Back to Dashboard
                    </a>
                </div>
            `;
        }
        
        if (lessonsContainer) {
            lessonsContainer.innerHTML = '';
        }
    }
}

// Initialize season view when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new SeasonView();
    });
} else {
    new SeasonView();
}
