/**
 * InnerVerse Learning Paths - Canvas Logic
 * =========================================
 * Handles 2D tree visualization, zoom/pan, API integration
 */

const CONFIG = {
    api: {
        baseUrl: '/api',
        courses: '/api/courses',
        generate: '/api/courses/generate',
        assignContent: '/api/courses/assign-content',
        stats: '/api/courses/stats'
    },
    canvas: {
        nodeWidth: 280,
        nodeHeight: 210,
        horizontalSpacing: 100,
        verticalSpacing: 150,
        minZoom: 0.3,
        maxZoom: 2,
        transitionDuration: 750
    },
    colors: {
        foundations: '#3b82f6',
        your_type: '#8b5cf6',
        relationships: '#ec4899',
        advanced: '#f59e0b'
    },
    statusIcons: {
        not_started: '●',
        in_progress: '●',
        completed: '✅',
        paused: '⏸'
    },
    categoryToDifficulty: {
        foundations: 'FOUNDATIONS',
        your_type: 'INTERMEDIATE',
        relationships: 'INTERMEDIATE',
        advanced: 'ADVANCED'
    }
};

const state = {
    courses: [],
    coursesGrouped: {},
    activeModal: null,
    selectedCourse: null,
    searchQuery: '',
    viewMode: 'tree'
};

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🎨 Initializing Learning Paths...');
    
    initializeCanvas();
    await loadCourses();
    setupEventListeners();
    
    console.log('✅ Learning Paths initialized');
});

let svg, g, zoom, simulation;

function initializeCanvas() {
    const container = d3.select('#canvas-container');
    svg = d3.select('#learning-canvas');
    
    g = svg.append('g');
    
    zoom = d3.zoom()
        .scaleExtent([CONFIG.canvas.minZoom, CONFIG.canvas.maxZoom])
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
        });
    
    svg.call(zoom);
    
    simulation = d3.forceSimulation()
        .force('charge', d3.forceManyBody().strength(-500))
        .force('center', d3.forceCenter())
        .force('collision', d3.forceCollide().radius(150));
}

async function loadCourses() {
    showLoading(true);
    
    try {
        const response = await fetch(CONFIG.api.courses);
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || 'Failed to load courses');
        }
        
        state.coursesGrouped = result.data;
        state.courses = [];
        
        for (const category in result.data) {
            state.courses.push(...result.data[category]);
        }
        
        console.log(`📚 Loaded ${state.courses.length} courses`);
        
        if (state.courses.length === 0) {
            showEmptyState();
        } else {
            renderCanvas();
        }
        
    } catch (error) {
        console.error('Error loading courses:', error);
        showToast('Error loading courses', error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function renderCanvas() {
    g.selectAll('*').remove();
    
    if (state.courses.length === 0) {
        return;
    }
    
    const treeData = buildTreeHierarchy(state.courses);
    
    const treeLayout = d3.tree()
        .nodeSize([
            CONFIG.canvas.nodeWidth + CONFIG.canvas.horizontalSpacing,
            CONFIG.canvas.nodeHeight + CONFIG.canvas.verticalSpacing
        ]);
    
    const root = d3.hierarchy(treeData);
    treeLayout(root);
    
    drawConnections(root.links());
    drawNodes(root.descendants());
    
    setTimeout(() => fitToView(), 100);
}

function buildTreeHierarchy(courses) {
    const grouped = state.coursesGrouped;
    
    const root = {
        id: 'root',
        name: 'Learning Paths',
        children: []
    };
    
    if (grouped.foundations && grouped.foundations.length > 0) {
        grouped.foundations.forEach(course => {
            root.children.push({
                id: course.id,
                name: course.title,
                category: course.category,
                data: course
            });
        });
    }
    
    const otherCategories = ['your_type', 'relationships', 'advanced'];
    otherCategories.forEach(category => {
        if (grouped[category] && grouped[category].length > 0) {
            grouped[category].forEach(course => {
                root.children.push({
                    id: course.id,
                    name: course.title,
                    category: course.category,
                    data: course
                });
            });
        }
    });
    
    if (root.children.length === 0) {
        root.children.push({
            id: 'placeholder',
            name: 'No courses yet',
            category: 'foundations',
            data: null
        });
    }
    
    return root;
}

function drawConnections(links) {
    const link = g.selectAll('.connection-line')
        .data(links)
        .enter()
        .append('path')
        .attr('class', 'connection-line')
        .attr('d', d3.linkVertical()
            .x(d => d.x)
            .y(d => d.y)
        );
}

function drawNodes(nodes) {
    const node = g.selectAll('.node')
        .data(nodes.filter(d => d.data.id !== 'root'), d => d.data.id)
        .enter()
        .append('g')
        .attr('class', 'node')
        .attr('transform', d => `translate(${d.x - CONFIG.canvas.nodeWidth / 2}, ${d.y})`)
        .on('click', (event, d) => {
            if (d.data.data) {
                openCourseModal(d.data.data);
            }
        });
    
    const fo = node.append('foreignObject')
        .attr('width', CONFIG.canvas.nodeWidth)
        .attr('height', CONFIG.canvas.nodeHeight);
    
    fo.append('xhtml:div')
        .attr('class', 'course-card')
        .html(d => renderCourseCard(d.data.data));
}

function renderCourseCard(course) {
    if (!course) return '<div class="course-card">Loading...</div>';
    
    const progress = calculateProgress(course);
    const status = determineStatus(course, progress);
    
    return `
        <div class="course-card-header">
            <span class="status-icon ${status.replace('_', '-')}">${CONFIG.statusIcons[status]}</span>
            <span class="category-badge category-${course.category}">
                ${CONFIG.categoryToDifficulty[course.category] || course.category.toUpperCase()}
            </span>
        </div>
        <div class="course-title">${course.title}</div>
        <div class="course-description">${course.description || 'No description'}</div>
        <div class="course-stats">
            <div class="stat">
                <span class="stat-label">Lessons</span>
                <span class="stat-value">${course.lesson_count || 0}</span>
            </div>
            <div class="stat">
                <span class="stat-label">Progress</span>
                <span class="stat-value">${progress}%</span>
            </div>
            <div class="stat">
                <span class="stat-label">Hours</span>
                <span class="stat-value">${course.estimated_hours || 0}h</span>
            </div>
        </div>
        <div class="progress-bar">
            <div class="progress-fill" style="width: ${progress}%"></div>
        </div>
    `;
}

function calculateProgress(course) {
    if (!course.completed_lesson_ids || course.completed_lesson_ids.length === 0) return 0;
    
    const completed = course.completed_lesson_ids.length;
    const total = course.lesson_count || 1;
    
    return Math.round((completed / total) * 100);
}

function determineStatus(course, progress) {
    // Check progress based on course properties (not course.progress)
    if (progress === 100) return 'completed';
    if (course.current_lesson_id) return 'in_progress';
    if (progress > 0 && progress < 100) return 'paused';
    
    return 'not_started';
}

async function openCourseModal(course) {
    state.selectedCourse = course;
    
    try {
        // Fetch course details and lessons in parallel
        const [courseResponse, lessonsResponse] = await Promise.all([
            fetch(`${CONFIG.api.courses}/${course.id}`),
            fetch(`${CONFIG.api.courses}/${course.id}/lessons`)
        ]);
        
        const courseResult = await courseResponse.json();
        const lessonsResult = await lessonsResponse.json();
        
        if (!courseResult.success) {
            throw new Error('Failed to load course details');
        }
        
        const fullCourse = courseResult.course;  // Fixed: use result.course not result.data
        const lessons = lessonsResult.success ? lessonsResult.lessons : [];
        
        document.getElementById('modal-course-title').textContent = fullCourse.title;
        document.getElementById('modal-category').textContent = fullCourse.category.replace('_', ' ');
        document.getElementById('modal-category').className = `category-badge category-${fullCourse.category}`;
        
        const progress = calculateProgress(fullCourse);
        document.getElementById('modal-progress').textContent = `${progress}% Complete`;
        document.getElementById('modal-hours').textContent = `${fullCourse.estimated_hours || 0} hours`;
        document.getElementById('modal-description').textContent = fullCourse.description || 'No description';
        
        renderLessonsList(lessons, fullCourse);
        
        const continueBtn = document.getElementById('continue-learning-btn');
        if (fullCourse.current_lesson_id) {
            continueBtn.style.display = 'block';
        } else {
            continueBtn.style.display = 'none';
        }
        
        document.getElementById('lesson-modal').style.display = 'flex';
        state.activeModal = 'lesson';
        
    } catch (error) {
        console.error('Error loading course details:', error);
        showToast('Error', error.message, 'error');
    }
}

function renderLessonsList(lessons, course) {
    const container = document.getElementById('lessons-list');
    
    if (lessons.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary); text-align: center;">No lessons yet</p>';
        return;
    }
    
    const completedIds = course?.completed_lesson_ids || [];
    const currentId = course?.current_lesson_id;
    
    container.innerHTML = lessons.map((lesson, index) => {
        let status = 'not-started';
        let statusIcon = '●';
        
        if (completedIds.includes(lesson.id)) {
            status = 'completed';
            statusIcon = '✅';
        } else if (lesson.id === currentId) {
            status = 'in-progress';
            statusIcon = '▶️';
        }
        
        return `
            <div class="lesson-item ${status}" data-lesson-id="${lesson.id}">
                <div class="lesson-number">${index + 1}</div>
                <div class="lesson-info">
                    <div class="lesson-title">${lesson.title}</div>
                    <div class="lesson-meta">
                        ${lesson.estimated_minutes || 30} min · ${lesson.difficulty || 'foundational'}
                    </div>
                </div>
                <div class="lesson-status">${statusIcon}</div>
            </div>
        `;
    }).join('');
    
    container.querySelectorAll('.lesson-item').forEach(item => {
        item.addEventListener('click', () => {
            const lessonId = item.dataset.lessonId;
            viewLesson(state.selectedCourse.id, lessonId);
        });
    });
}

function closeModal() {
    if (state.activeModal === 'lesson') {
        document.getElementById('lesson-modal').style.display = 'none';
    } else if (state.activeModal === 'generate') {
        document.getElementById('generate-modal').style.display = 'none';
    }
    state.activeModal = null;
    state.selectedCourse = null;
}

function viewLesson(courseId, lessonId) {
    window.location.href = `/learning-paths/${courseId}/${lessonId}`;
}

function openGenerateModal() {
    document.getElementById('generate-modal').style.display = 'flex';
    document.getElementById('generation-result').style.display = 'none';
    document.getElementById('generate-form').reset();
    state.activeModal = 'generate';
}

async function handleGenerateSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const data = {
        user_goal: formData.get('user_goal'),
        max_lessons: parseInt(formData.get('max_lessons')),
        target_category: formData.get('target_category') || null
    };
    
    const submitBtn = document.getElementById('submit-generate-btn');
    submitBtn.disabled = true;
    document.querySelector('.btn-text').style.display = 'none';
    document.querySelector('.btn-loading').style.display = 'flex';
    
    try {
        const response = await fetch(CONFIG.api.generate, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || 'Generation failed');
        }
        
        document.getElementById('generate-form').style.display = 'none';
        document.getElementById('generation-result').style.display = 'block';
        
        // Handle multi-course response
        const totalCourses = result.total_courses || 1;
        const totalLessons = result.total_lessons || result.course?.lesson_count || 0;
        const pathType = result.path_type || 'simple';
        
        if (totalCourses > 1) {
            // Multi-course learning path
            const courseList = result.courses.map(c => c.title).join(', ');
            document.getElementById('generated-course-title').textContent = 
                `Learning Path: ${totalCourses} Courses (${pathType})`;
            document.getElementById('generated-course-info').textContent = 
                `${totalLessons} total lessons · ${totalCourses} courses · Cost: $${result.cost.toFixed(4)}`;
        } else {
            // Single course (backwards compatible)
            document.getElementById('generated-course-title').textContent = result.course.title;
            document.getElementById('generated-course-info').textContent = 
                `${result.course.lesson_count} lessons · ${result.course.estimated_hours}h · Cost: $${result.cost.toFixed(4)}`;
        }
        
        state.generatedCourseId = result.course_id;
        
        const message = totalCourses > 1 
            ? `Generated ${totalCourses}-course learning path!` 
            : `Generated "${result.course.title}"`;
        showToast('Success!', message, 'success');
        
        setTimeout(async () => {
            await loadCourses();
            renderCanvas();  // Re-render tree with new courses
            closeModal();  // Auto-close modal after refresh
        }, 1500);  // Give it 1.5 seconds
        
    } catch (error) {
        console.error('Generation error:', error);
        showToast('Generation Failed', error.message, 'error');
    } finally {
        submitBtn.disabled = false;
        document.querySelector('.btn-text').style.display = 'block';
        document.querySelector('.btn-loading').style.display = 'none';
    }
}

function fitToView() {
    const bounds = g.node().getBBox();
    const parent = svg.node().getBoundingClientRect();
    
    const fullWidth = bounds.width;
    const fullHeight = bounds.height;
    const width = parent.width;
    const height = parent.height;
    
    const midX = bounds.x + fullWidth / 2;
    const midY = bounds.y + fullHeight / 2;
    
    const scale = 0.8 / Math.max(fullWidth / width, fullHeight / height);
    const translate = [width / 2 - scale * midX, height / 2 - scale * midY];
    
    svg.transition()
        .duration(CONFIG.canvas.transitionDuration)
        .call(zoom.transform, d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale));
}

function zoomIn() {
    svg.transition()
        .duration(300)
        .call(zoom.scaleBy, 1.3);
}

function zoomOut() {
    svg.transition()
        .duration(300)
        .call(zoom.scaleBy, 0.7);
}

function resetView() {
    svg.transition()
        .duration(CONFIG.canvas.transitionDuration)
        .call(zoom.transform, d3.zoomIdentity);
}

function handleSearch() {
    const query = document.getElementById('search-input').value.toLowerCase();
    state.searchQuery = query;
    
    if (!query) {
        g.selectAll('.node').style('opacity', 1);
        return;
    }
    
    g.selectAll('.node').each(function(d) {
        const course = d.data.data;
        if (!course) return;
        
        const matches = 
            course.title.toLowerCase().includes(query) ||
            (course.description && course.description.toLowerCase().includes(query)) ||
            (course.tags && course.tags.some(tag => tag.toLowerCase().includes(query)));
        
        d3.select(this).style('opacity', matches ? 1 : 0.2);
    });
}

function showLoading(show) {
    document.getElementById('loading-state').style.display = show ? 'flex' : 'none';
}

function showEmptyState() {
    document.getElementById('empty-state').style.display = 'flex';
    document.getElementById('learning-canvas').style.display = 'none';
}

function showToast(title, message, type = 'info') {
    const container = document.getElementById('toast-container');
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icon = {
        success: '✅',
        error: '❌',
        info: 'ℹ️',
        warning: '⚠️'
    }[type];
    
    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <div class="toast-message">
            <strong>${title}</strong>
            <p>${message}</p>
        </div>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function setupEventListeners() {
    document.getElementById('search-btn').addEventListener('click', handleSearch);
    document.getElementById('search-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });
    
    document.getElementById('reset-view-btn').addEventListener('click', resetView);
    document.getElementById('zoom-in').addEventListener('click', zoomIn);
    document.getElementById('zoom-out').addEventListener('click', zoomOut);
    document.getElementById('fit-view').addEventListener('click', fitToView);
    
    document.getElementById('close-modal').addEventListener('click', closeModal);
    document.getElementById('close-generate-modal').addEventListener('click', closeModal);
    
    document.getElementById('create-first-course-btn').addEventListener('click', openGenerateModal);
    document.getElementById('generate-course-btn').addEventListener('click', openGenerateModal);
    document.getElementById('view-mode-toggle').addEventListener('click', () => {
        showToast('Info', 'Grid view coming in Phase 4!', 'info');
    });
    
    document.getElementById('generate-form').addEventListener('submit', handleGenerateSubmit);
    document.getElementById('cancel-generate-btn').addEventListener('click', closeModal);
    
    document.getElementById('view-course-btn').addEventListener('click', () => {
        if (state.selectedCourse) {
            showToast('Info', 'Course detail page coming in Phase 4!', 'info');
        }
    });
    
    document.getElementById('view-generated-course-btn').addEventListener('click', () => {
        closeModal();
        showToast('Success', 'Course added to canvas!', 'success');
    });
    
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && state.activeModal) {
            closeModal();
        }
        if (e.key === ' ' && !state.activeModal) {
            e.preventDefault();
            resetView();
        }
    });
}

window.LearningPaths = {
    state,
    loadCourses,
    renderCanvas,
    openGenerateModal,
    fitToView
};
