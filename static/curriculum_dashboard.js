// ==============================================================================
// PHASE 7.1: CURRICULUM DASHBOARD JAVASCRIPT
// ==============================================================================

class CurriculumDashboard {
    constructor() {
        this.curriculumData = null;
        this.continueData = null;
        this.theme = localStorage.getItem('theme') || 'dark';
        
        this.init();
    }

    async init() {
        this.applyTheme();
        this.setupEventListeners();
        
        await this.loadAllData();
    }

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

    setupEventListeners() {
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }

        const continueBtn = document.getElementById('continueBtn');
        if (continueBtn) {
            continueBtn.addEventListener('click', () => this.onContinueLearning());
        }
    }

    async loadAllData() {
        try {
            console.log('🔵 Starting loadAllData...');
            const [curriculumResponse, continueResponse] = await Promise.all([
                fetch('/api/curriculum/summary'),
                fetch('/api/progress/continue')
            ]);

            console.log('🔵 API responses received:', curriculumResponse.status, continueResponse.status);

            if (!curriculumResponse.ok || !continueResponse.ok) {
                throw new Error('Failed to load curriculum data');
            }

            this.curriculumData = await curriculumResponse.json();
            this.continueData = await continueResponse.json();

            console.log('🔵 Data loaded:', this.curriculumData, this.continueData);

            this.renderProgressOverview();
            console.log('🔵 Progress overview rendered');
            
            this.renderContinueLearning();
            console.log('🔵 Continue banner rendered');
            
            this.renderModules();
            console.log('🔵 Modules rendered');

        } catch (error) {
            console.error('❌ Error loading curriculum:', error);
            this.showError('Failed to load curriculum. Please refresh the page.');
        }
    }

    renderProgressOverview() {
        const total_lessons = this.curriculumData.total_lessons;
        const total_completed = this.curriculumData.total_completed;
        const percentage = total_lessons > 0 
            ? Math.round((total_completed / total_lessons) * 100) 
            : 0;

        document.getElementById('overallProgress').textContent = 
            `${total_completed} of ${total_lessons}`;
        
        document.getElementById('completionPercent').textContent = 
            `${percentage}%`;

        const progressBar = document.getElementById('progressBar');
        if (progressBar) {
            setTimeout(() => {
                progressBar.style.width = `${percentage}%`;
            }, 100);
        }
    }

    renderContinueLearning() {
        const banner = document.getElementById('continueLearning');
        if (!banner || !this.continueData) return;

        const lesson_title = this.continueData.lesson_title;
        const module_name = this.continueData.module_name;
        const season_name = this.continueData.season_name;
        const season_number = this.continueData.season_number;
        const lesson_number = this.continueData.lesson_number;

        document.getElementById('continueTitle').textContent = lesson_title;
        
        const meta = `${module_name} • Season ${season_number}: ${season_name} • Lesson ${lesson_number}`;
        document.getElementById('continueMeta').textContent = meta;

        banner.style.display = 'block';
    }

    renderModules() {
        const container = document.getElementById('modulesContainer');
        if (!container) return;

        if (!this.curriculumData || !this.curriculumData.modules) {
            console.error('❌ No curriculum data or modules to render');
            return;
        }

        const modules = this.curriculumData.modules;

        container.innerHTML = '';

        modules.forEach(module => {
            const moduleCard = this.createModuleCard(module);
            container.appendChild(moduleCard);
        });
    }

    createModuleCard(module) {
        const module_number = module.module_number;
        const module_name = module.module_name;
        const total_lessons = module.total_lessons;
        const completed_lessons = module.completed_lessons;
        const seasons = module.seasons;

        const percentage = total_lessons > 0 
            ? Math.round((completed_lessons / total_lessons) * 100) 
            : 0;

        const card = document.createElement('div');
        card.className = 'module-card';
        card.innerHTML = `
            <div class="module-header">
                <h2 class="module-title">
                    <span class="module-number">Module ${module_number}:</span>
                    ${module_name}
                </h2>
                <div class="module-progress">
                    <div class="module-progress-text">
                        ${completed_lessons}/${total_lessons} Complete
                    </div>
                    <div class="module-progress-meta">${percentage}%</div>
                </div>
            </div>
            <div class="seasons-grid" id="seasons-module-${module_number}">
            </div>
        `;

        const seasonsContainer = card.querySelector(`#seasons-module-${module_number}`);
        seasons.forEach(season => {
            const seasonCard = this.createSeasonCard(season);
            seasonsContainer.appendChild(seasonCard);
        });

        return card;
    }

    createSeasonCard(season) {
        const season_number = season.season_number;
        const season_name = season.season_name;
        const lesson_count = season.lesson_count;
        const completed_count = season.completed_count;
        const last_accessed = season.last_accessed;

        const card = document.createElement('div');
        card.className = 'season-card';
        card.dataset.seasonNumber = season_number;

        let accessedText = '';
        if (last_accessed) {
            const date = new Date(last_accessed);
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
            <div class="season-header">
                <div>
                    <div class="season-title">${season_name}</div>
                    <div class="season-number">Season ${season_number}</div>
                </div>
                <div class="season-progress-badge">
                    ${completed_count}/${lesson_count}
                </div>
            </div>
            <div class="season-meta">
                <div class="season-lesson-count">
                    📚 ${lesson_count} lessons
                </div>
                ${accessedText ? `<div class="season-last-accessed">${accessedText}</div>` : ''}
            </div>
        `;

        card.addEventListener('click', () => {
            this.onSeasonClick(season_number);
        });

        return card;
    }

    onContinueLearning() {
        if (!this.continueData) return;
        
        const lesson_id = this.continueData.lesson_id;
        
        window.location.href = `/lesson/${lesson_id}`;
    }

    onSeasonClick(seasonNumber) {
        window.location.href = `/season/${seasonNumber}`;
    }

    showError(message) {
        const container = document.getElementById('modulesContainer');
        if (!container) return;

        container.innerHTML = `
            <div style="text-align: center; padding: 40px; color: var(--text-secondary);">
                <p style="font-size: 18px; margin-bottom: 16px;">⚠️ ${message}</p>
                <button onclick="location.reload()" style="
                    background: var(--accent-primary);
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 16px;
                ">
                    Retry
                </button>
            </div>
        `;
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new CurriculumDashboard();
    });
} else {
    new CurriculumDashboard();
}
