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
    // Create map of courses by ID
    const courseMap = {};
    courses.forEach(course => {
        courseMap[course.id] = {
            id: course.id,
            name: course.title,
            category: course.category,
            data: course,
            children: []
        };
    });
    
    // Build parent-child relationships using prerequisite_course_id
    const rootNodes = [];
    courses.forEach(course => {
        const node = courseMap[course.id];
        
        if (course.prerequisite_course_id) {
            // Has prerequisite - add as child of parent
            const parent = courseMap[course.prerequisite_course_id];
            if (parent) {
                parent.children.push(node);
            } else {
                // Parent not found - treat as root
                rootNodes.push(node);
            }
        } else {
            // No prerequisite - this is a root node
            rootNodes.push(node);
        }
    });
    
    // Handle empty state
    if (rootNodes.length === 0 && courses.length === 0) {
        rootNodes.push({
            id: 'placeholder',
            name: 'No courses yet',
            category: 'foundations',
            data: null,
            children: []
        });
    }
    
    // Create root container
    return {
        id: 'root',
        name: 'Learning Paths',
        children: rootNodes
    };
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
        <div class="course-card-top">
            <span class="category-badge category-${course.category}">
                ${CONFIG.categoryToDifficulty[course.category] || course.category.toUpperCase()}
            </span>
            <button class="delete-course-btn" onclick="handleDeleteCourse(event, '${course.id}', '${course.title.replace(/'/g, "&apos;")}')">🗑️</button>
        </div>
        <div class="course-card-header">
            <span class="status-icon ${status.replace('_', '-')}">${CONFIG.statusIcons[status]}</span>
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
        
        // Store lessons in state for "View Course Details" button
        state.selectedCourseLessons = lessons;
        
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

// Delete course with 2-step confirmation (Phase 6.5)
// Make globally accessible for onclick handlers
window.handleDeleteCourse = async function(event, courseId, courseTitle) {
    // Stop event propagation to prevent opening the modal
    event.stopPropagation();
    event.preventDefault();
    
    // First confirmation
    const confirm1 = confirm(
        `⚠️ Delete this course?\n\n"${courseTitle}"\n\nThis will delete all lessons and concept assignments.`
    );
    
    if (!confirm1) return;
    
    // Second confirmation
    const confirm2 = confirm('🚨 Are you SURE? This cannot be undone!');
    
    if (!confirm2) return;
    
    try {
        showLoading(true);
        
        const response = await fetch(`/api/courses/${courseId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Success', data.message, 'success');
            // Reload courses to update the view
            await loadCourses();
        } else {
            showToast('Error', data.error || 'Failed to delete course', 'error');
        }
    } catch (error) {
        showToast('Error', 'Failed to delete: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
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
        console.log('🚀 Sending course generation request:', data);
        
        const response = await fetch(CONFIG.api.generate, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        console.log('📡 Response status:', response.status, response.statusText);
        
        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('❌ Non-JSON response:', text);
            throw new Error(`Server returned non-JSON response: ${text.substring(0, 200)}`);
        }
        
        const result = await response.json();
        console.log('✅ Parsed result:', result);
        
        if (!response.ok) {
            throw new Error(result.detail || result.error || `Server error: ${response.status}`);
        }
        
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
        
        // NEW ASYNC RESPONSE: Backend returns job_id immediately
        const structureJobId = result.job_id || result.structure_job_id;
        
        if (!structureJobId) {
            throw new Error("No job_id returned from server");
        }
        
        console.log(`🏗️ Course structure generation started (job ${structureJobId})`);
        showToast('Generating Course...', 'Course structure generation started', 'info');
        
        // Poll for structure generation progress
        pollStructureGenerationProgress(structureJobId);
        
    } catch (error) {
        console.error('❌ Generation error:', error);
        console.error('Error details:', {
            message: error.message,
            stack: error.stack,
            response: error.response
        });
        
        // Show error message that stays longer
        const errorMsg = error.message || 'Unknown error occurred';
        alert(`Course Generation Failed:\n\n${errorMsg}\n\nCheck browser console (F12) for details.`);
        showToast('Generation Failed', errorMsg, 'error');
    } finally {
        submitBtn.disabled = false;
        document.querySelector('.btn-text').style.display = 'block';
        document.querySelector('.btn-loading').style.display = 'none';
    }
}

async function pollStructureGenerationProgress(jobId) {
    let pollInterval = null;
    let pollCount = 0;
    const maxPolls = 150; // 5 minutes max (150 * 2s)
    
    console.log(`🏗️ Starting structure generation polling for job ${jobId}`);
    
    // Show progress in result div
    document.getElementById('generate-form').style.display = 'none';
    document.getElementById('generation-result').style.display = 'block';
    document.getElementById('generated-course-title').textContent = 'Generating Course Structure...';
    document.getElementById('generated-course-info').textContent = 'Calling Claude API to design your learning path...';
    
    pollInterval = setInterval(async () => {
        pollCount++;
        
        if (pollCount > maxPolls) {
            clearInterval(pollInterval);
            showToast('Timeout', 'Generation took too long. Please try again.', 'error');
            return;
        }
        
        try {
            const response = await fetch(`/api/courses/structure-generation/${jobId}`);
            const data = await response.json();
            
            console.log(`📊 Structure job ${jobId} status:`, data.status);
            
            if (data.status === 'completed') {
                clearInterval(pollInterval);
                
                // Structure generation complete!
                const courses = data.courses_created || [];
                const totalLessons = courses.reduce((sum, c) => sum + (c.lesson_count || 0), 0);
                
                console.log(`✅ Structure complete! ${courses.length} courses, ${totalLessons} lessons`);
                
                // Update UI
                if (courses.length > 1) {
                    document.getElementById('generated-course-title').textContent = 
                        `Learning Path: ${courses.length} Courses`;
                    document.getElementById('generated-course-info').textContent = 
                        `${totalLessons} total lessons · ${courses.length} courses · Cost: $${data.cost.toFixed(4)}`;
                } else if (courses.length === 1) {
                    document.getElementById('generated-course-title').textContent = courses[0].title;
                    document.getElementById('generated-course-info').textContent = 
                        `${courses[0].lesson_count} lessons · Cost: $${data.cost.toFixed(4)}`;
                }
                
                showToast('Success!', `Course structure created! Generating lesson content...`, 'success');
                
                // Reload courses to show the new ones
                await loadCourses();
                if (state.viewMode === 'grid') {
                    renderGridView();
                } else {
                    renderCanvas();
                }
                
                // Start polling for lesson content generation if there's a content job
                if (data.content_job_id) {
                    console.log(`📝 Starting content generation polling for job ${data.content_job_id}`);
                    pollContentGenerationProgress(data.content_job_id, courses.length > 1);
                } else {
                    // No content generation, close modal
                    setTimeout(() => closeModal(), 1500);
                }
                
            } else if (data.status === 'failed') {
                clearInterval(pollInterval);
                showToast('Error', data.error_message || 'Generation failed', 'error');
                console.error('❌ Structure generation failed:', data.error_message);
            }
            // else: still processing, keep polling
            
        } catch (error) {
            console.error('❌ Polling error:', error);
            clearInterval(pollInterval);
            showToast('Error', 'Failed to check generation status', 'error');
        }
    }, 2000); // Poll every 2 seconds
}

async function pollContentGenerationProgress(jobId, isMultiCourse) {
    let pollInterval = null;
    let pollCount = 0;
    const maxPolls = 300; // 10 minutes max (300 * 2s)
    
    // Create progress display element
    const resultDiv = document.getElementById('generation-result');
    const progressDiv = document.createElement('div');
    progressDiv.id = 'content-generation-progress';
    progressDiv.style.cssText = 'margin-top: 16px; padding: 16px; background: rgba(var(--teal-rgb), 0.1); border-radius: 12px; border: 1px solid var(--teal);';
    progressDiv.innerHTML = `
        <div style="font-size: 14px; color: var(--teal); font-weight: 600; margin-bottom: 8px;">
            📝 Generating lesson content...
        </div>
        <div id="progress-status" style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">
            Starting...
        </div>
        <div style="background: rgba(255,255,255,0.2); height: 8px; border-radius: 4px; overflow: hidden;">
            <div id="progress-bar" style="background: var(--teal); height: 100%; width: 0%; transition: width 0.3s ease;"></div>
        </div>
        <div id="progress-cost" style="font-size: 12px; color: var(--text-tertiary); margin-top: 8px; text-align: right;">
            Cost: $0.0000
        </div>
    `;
    resultDiv.appendChild(progressDiv);
    
    const pollOnce = async () => {
        try {
            pollCount++;
            
            const response = await fetch(`/api/courses/content-generation/${jobId}`);
            const data = await response.json();
            
            if (!data.success) {
                throw new Error('Failed to fetch job status');
            }
            
            const { status, progress, cost } = data;
            const { total_lessons, completed, failed, percent } = progress;
            
            // Update progress UI
            document.getElementById('progress-status').textContent = 
                `${completed} of ${total_lessons} lessons complete · ${failed} skipped`;
            document.getElementById('progress-bar').style.width = `${percent}%`;
            document.getElementById('progress-cost').textContent = 
                `Cost: $${cost.toFixed(4)}`;
            
            console.log(`📝 Content gen progress: ${completed}/${total_lessons} (${percent}%)`);
            
            // Check if job is complete
            if (status === 'completed' || status === 'completed_with_errors' || status === 'failed') {
                clearInterval(pollInterval);
                
                if (status === 'completed') {
                    progressDiv.querySelector('div').innerHTML = '✅ Lesson content generated!';
                    showToast('Success!', `Generated content for ${completed} lessons`, 'success');
                } else if (status === 'completed_with_errors') {
                    progressDiv.querySelector('div').innerHTML = `⚠️ Content generated with ${failed} failures`;
                    showToast('Partial Success', `${completed} lessons generated, ${failed} failed`, 'warning');
                } else {
                    progressDiv.querySelector('div').innerHTML = '❌ Content generation failed';
                    showToast('Error', data.error_message || 'Content generation failed', 'error');
                }
                
                // Reload courses and close modal after 2 seconds
                setTimeout(async () => {
                    await loadCourses();
                    renderCanvas();
                    closeModal();
                }, 2000);
            }
            
            // Safety check: stop polling after max attempts
            if (pollCount >= maxPolls) {
                clearInterval(pollInterval);
                progressDiv.querySelector('div').innerHTML = '⏱️ Content generation taking longer than expected...';
                showToast('Info', 'Content generation is still running. Check back later.', 'info');
                setTimeout(async () => {
                    await loadCourses();
                    renderCanvas();
                    closeModal();
                }, 2000);
            }
            
        } catch (error) {
            console.error('Polling error:', error);
            // Don't stop polling on error, just log it
        }
    };
    
    // Start polling immediately, then every 2 seconds
    await pollOnce();
    pollInterval = setInterval(pollOnce, 2000);
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

function toggleViewMode() {
    state.viewMode = state.viewMode === 'tree' ? 'grid' : 'tree';
    
    const canvas = document.getElementById('learning-canvas');
    const gridView = document.getElementById('grid-view');
    const zoomControls = document.getElementById('zoom-controls');
    const icon = document.getElementById('view-mode-icon');
    const label = document.getElementById('view-mode-label');
    
    if (state.viewMode === 'grid') {
        // Switch to grid view
        canvas.style.display = 'none';
        gridView.style.display = 'grid';
        zoomControls.style.display = 'none';
        icon.textContent = '🌳';
        label.textContent = 'Tree View';
        renderGridView();
    } else {
        // Switch to tree view
        canvas.style.display = 'block';
        gridView.style.display = 'none';
        zoomControls.style.display = 'flex';
        icon.textContent = '📊';
        label.textContent = 'Grid View';
        renderCanvas();
    }
}

function renderGridView() {
    const gridContainer = document.getElementById('grid-view');
    gridContainer.innerHTML = '';
    
    if (!state.courses || state.courses.length === 0) {
        return;
    }
    
    // Group courses by category
    const categories = ['foundations', 'your_type', 'relationships', 'advanced', 'integration', 'intermediate'];
    const grouped = {};
    
    categories.forEach(cat => {
        grouped[cat] = state.courses.filter(c => c.category === cat);
    });
    
    // Render each category
    Object.entries(grouped).forEach(([category, courses]) => {
        if (courses.length === 0) return;
        
        const section = document.createElement('div');
        section.className = 'grid-category-section';
        section.innerHTML = `
            <h3 class="grid-category-title">${category.replace('_', ' ').toUpperCase()}</h3>
            <div class="grid-cards"></div>
        `;
        
        const cardsContainer = section.querySelector('.grid-cards');
        
        courses.forEach(course => {
            const card = document.createElement('div');
            card.className = 'grid-course-card';
            card.style.borderLeft = `4px solid ${CONFIG.colors[category]}`;
            
            card.innerHTML = `
                <div class="grid-card-header">
                    <h4>${course.title}</h4>
                    <span class="category-badge" style="background: ${CONFIG.colors[category]}">${category.replace('_', ' ')}</span>
                </div>
                <div class="grid-card-body">
                    <p class="grid-card-description">${course.description || 'No description'}</p>
                    <div class="grid-card-meta">
                        <span>📚 ${course.lesson_count || 0} lessons</span>
                        <span>⏱️ ${course.estimated_hours || 0}h</span>
                        <span class="status-dot ${course.status || 'not-started'}">●</span>
                    </div>
                </div>
                <div class="grid-card-actions">
                    <button class="grid-btn-primary" onclick="window.LearningPaths.viewCourse(${course.id})">
                        View Course
                    </button>
                    <button class="grid-btn-delete" onclick="window.LearningPaths.deleteCourse(${course.id}, event)">
                        🗑️
                    </button>
                </div>
            `;
            
            cardsContainer.appendChild(card);
        });
        
        gridContainer.appendChild(section);
    });
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
    document.getElementById('view-mode-toggle').addEventListener('click', toggleViewMode);
    
    document.getElementById('generate-form').addEventListener('submit', handleGenerateSubmit);
    document.getElementById('cancel-generate-btn').addEventListener('click', closeModal);
    
    document.getElementById('view-course-btn').addEventListener('click', () => {
        if (state.selectedCourse && state.selectedCourseLessons && state.selectedCourseLessons.length > 0) {
            // Navigate to first lesson to start the course
            const firstLesson = state.selectedCourseLessons[0];
            viewLesson(state.selectedCourse.id, firstLesson.id);
        } else if (state.selectedCourse) {
            showToast('Error', 'No lessons available in this course', 'error');
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

// Helper to find course by ID and open modal
function viewCourseById(courseId) {
    const course = state.courses.find(c => c.id === parseInt(courseId));
    if (course) {
        openCourseModal(course);
    } else {
        showToast('Error', 'Course not found', 'error');
    }
}

window.LearningPaths = {
    state,
    loadCourses,
    renderCanvas,
    renderGridView,
    toggleViewMode,
    openGenerateModal,
    fitToView,
    viewCourse: viewCourseById,
    deleteCourse: confirmDeleteCourse
};
