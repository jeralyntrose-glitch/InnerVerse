/**
 * YouTube Library Import Module
 * 
 * Handles CSV upload, match result display, and pending video review/linking
 */

(function() {
  'use strict';
  
  // State management
  const state = {
    selectedFile: null,
    pendingVideos: [],
    filteredVideos: [],
    currentFilter: 'all',
    currentPage: 1,
    pageSize: 50
  };
  
  // Initialize when DOM is ready
  function initYouTubeImport() {
    console.log('🎬 Initializing YouTube Import UI...');
    
    // Toggle section behavior
    initToggleSection();
    
    // CSV upload handlers
    initCSVUpload();
    
    // Pending videos handlers
    initPendingReview();
    
    console.log('✅ YouTube Import UI initialized');
  }
  
  /**
   * Initialize collapsible section toggle
   */
  function initToggleSection() {
    const toggle = document.getElementById('youtube-import-toggle');
    const content = document.getElementById('youtube-import-content');
    const chevron = toggle.querySelector('.youtube-import-chevron');
    
    if (!toggle || !content) {
      console.error('❌ YouTube import section elements not found');
      return;
    }
    
    toggle.addEventListener('click', function() {
      const isExpanded = content.classList.toggle('active');
      chevron.style.transform = isExpanded ? 'rotate(180deg)' : 'rotate(0deg)';
      
      if (!isExpanded) {
        content.style.maxHeight = '0';
      } else {
        content.style.maxHeight = content.scrollHeight + 'px';
      }
    });
  }
  
  /**
   * Initialize CSV upload functionality
   */
  function initCSVUpload() {
    const fileInput = document.getElementById('csv-file-input');
    const fileLabel = document.querySelector('.btn-csv-upload');
    const fileName = document.getElementById('csv-file-name');
    const importBtn = document.getElementById('import-csv-btn');
    
    if (!fileInput || !fileName || !importBtn) {
      console.error('❌ CSV upload elements not found');
      return;
    }
    
    // File selection
    fileInput.addEventListener('change', function(e) {
      const file = e.target.files[0];
      if (!file) return;
      
      if (!file.name.endsWith('.csv')) {
        showError('Please select a CSV file');
        return;
      }
      
      state.selectedFile = file;
      fileName.textContent = `📄 ${file.name}`;
      fileName.classList.remove('hidden');
      importBtn.classList.remove('hidden');
      
      console.log('✅ CSV file selected:', file.name);
    });
    
    // Import button
    importBtn.addEventListener('click', async function() {
      if (!state.selectedFile) {
        showError('Please select a CSV file first');
        return;
      }
      
      await uploadAndProcessCSV(state.selectedFile);
    });
  }
  
  /**
   * Upload CSV file and process matches
   */
  async function uploadAndProcessCSV(file) {
    const progressDiv = document.getElementById('csv-import-progress');
    const statusText = progressDiv.querySelector('.import-status-text');
    const progressBar = progressDiv.querySelector('.import-progress-bar');
    const summaryDiv = document.getElementById('match-results-summary');
    const importBtn = document.getElementById('import-csv-btn');
    
    try {
      // Show progress
      progressDiv.classList.remove('hidden');
      summaryDiv.classList.add('hidden');
      importBtn.disabled = true;
      statusText.textContent = 'Uploading CSV...';
      progressBar.style.width = '20%';
      
      // Create form data
      const formData = new FormData();
      formData.append('file', file);
      
      console.log('📤 Uploading CSV:', file.name);
      
      // Upload and process
      statusText.textContent = 'Processing videos and matching to lessons...';
      progressBar.style.width = '50%';
      
      const response = await fetch('/api/youtube/import', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Import failed');
      }
      
      const result = await response.json();
      console.log('✅ Import complete:', result);
      
      // Update UI
      progressBar.style.width = '100%';
      statusText.textContent = 'Processing complete!';
      
      // Show results after delay
      setTimeout(() => {
        progressDiv.classList.add('hidden');
        displayMatchResults(result.summary);
        showSuccess(`Processed ${result.summary.total_videos} videos successfully!`);
      }, 500);
      
    } catch (error) {
      console.error('❌ CSV import error:', error);
      progressDiv.classList.add('hidden');
      showError(`Import failed: ${error.message}`);
    } finally {
      importBtn.disabled = false;
    }
  }
  
  /**
   * Display match results summary
   */
  function displayMatchResults(summary) {
    const summaryDiv = document.getElementById('match-results-summary');
    
    document.getElementById('stat-high').textContent = summary.high_confidence;
    document.getElementById('stat-medium').textContent = summary.medium_confidence;
    document.getElementById('stat-low').textContent = summary.low_confidence;
    document.getElementById('stat-unmatched').textContent = summary.unmatched;
    
    summaryDiv.classList.remove('hidden');
    
    console.log('📊 Match results displayed:', summary);
  }
  
  /**
   * Initialize pending videos review
   */
  function initPendingReview() {
    const viewBtn = document.getElementById('view-pending-btn');
    const pendingSection = document.getElementById('pending-videos-section');
    const filterBtns = document.querySelectorAll('.filter-btn');
    
    if (!viewBtn || !pendingSection) {
      console.error('❌ Pending review elements not found');
      return;
    }
    
    // View pending button
    viewBtn.addEventListener('click', async function() {
      if (pendingSection.classList.contains('hidden')) {
        pendingSection.classList.remove('hidden');
        await loadPendingVideos();
      } else {
        pendingSection.classList.add('hidden');
      }
    });
    
    // Filter buttons
    filterBtns.forEach(btn => {
      btn.addEventListener('click', function() {
        filterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.currentFilter = btn.dataset.filter;
        state.currentPage = 1;
        filterAndRenderPendingVideos();
      });
    });
  }
  
  /**
   * Load pending videos from API
   */
  async function loadPendingVideos() {
    const listDiv = document.getElementById('pending-videos-list');
    
    try {
      listDiv.innerHTML = '<div class="pending-placeholder">Loading pending videos...</div>';
      
      console.log('📡 Fetching pending videos...');
      const response = await fetch('/api/youtube/pending');
      
      if (!response.ok) {
        throw new Error('Failed to fetch pending videos');
      }
      
      const data = await response.json();
      state.pendingVideos = data.pending_videos;
      console.log(`✅ Loaded ${state.pendingVideos.length} pending videos`);
      
      filterAndRenderPendingVideos();
      
    } catch (error) {
      console.error('❌ Error loading pending videos:', error);
      listDiv.innerHTML = `<div class="error-message">Error loading pending videos: ${error.message}</div>`;
    }
  }
  
  /**
   * Filter and render pending videos with pagination
   */
  function filterAndRenderPendingVideos() {
    // Filter videos
    if (state.currentFilter === 'all') {
      state.filteredVideos = state.pendingVideos;
    } else {
      state.filteredVideos = state.pendingVideos.filter(v => v.status === state.currentFilter);
    }
    
    // Paginate
    const startIdx = (state.currentPage - 1) * state.pageSize;
    const endIdx = startIdx + state.pageSize;
    const page = state.filteredVideos.slice(startIdx, endIdx);
    
    const listDiv = document.getElementById('pending-videos-list');
    
    if (state.filteredVideos.length === 0) {
      listDiv.innerHTML = '<div class="pending-placeholder">No pending videos found</div>';
      return;
    }
    
    // Render videos
    listDiv.innerHTML = page.map(video => renderPendingVideoCard(video)).join('');
    
    // Add link button handlers
    document.querySelectorAll('.btn-link-video').forEach(btn => {
      btn.addEventListener('click', function() {
        const videoId = parseInt(btn.dataset.videoId);
        showLinkingModal(videoId);
      });
    });
    
    // Render pagination
    renderPagination();
  }
  
  /**
   * Render a single pending video card
   */
  function renderPendingVideoCard(video) {
    const confidenceClass = video.confidence_score >= 0.7 ? 'medium' : 
                           video.confidence_score >= 0.5 ? 'low' : 'unmatched';
    const statusBadge = video.status === 'unmatched' ? '❌ Unmatched' : '⚠️ Needs Review';
    
    return `
      <div class="pending-video-card" data-video-id="${video.id}">
        <div class="video-info">
          <div class="video-title">${escapeHtml(video.title)}</div>
          <div class="video-meta">
            <span class="video-season">Season ${video.season || 'Unknown'}</span>
            <span class="video-confidence confidence-${confidenceClass}">
              ${(video.confidence_score * 100).toFixed(1)}% match
            </span>
            <span class="video-status">${statusBadge}</span>
          </div>
          ${video.matched_lesson_id ? `<div class="suggested-lesson">Suggested: Lesson ${video.matched_lesson_id}</div>` : ''}
        </div>
        <div class="video-actions">
          <a href="${video.source_url}" target="_blank" class="btn-view-video" title="View on YouTube">
            🎬 View
          </a>
          <button class="btn-link-video" data-video-id="${video.id}">
            🔗 Link to Lesson
          </button>
        </div>
      </div>
    `;
  }
  
  /**
   * Render pagination controls
   */
  function renderPagination() {
    const totalPages = Math.ceil(state.filteredVideos.length / state.pageSize);
    if (totalPages <= 1) return;
    
    const listDiv = document.getElementById('pending-videos-list');
    const paginationHTML = `
      <div class="pagination">
        <button class="page-btn" ${state.currentPage === 1 ? 'disabled' : ''} onclick="window.youtubeImport.prevPage()">
          ← Previous
        </button>
        <span class="page-info">
          Page ${state.currentPage} of ${totalPages} (${state.filteredVideos.length} videos)
        </span>
        <button class="page-btn" ${state.currentPage === totalPages ? 'disabled' : ''} onclick="window.youtubeImport.nextPage()">
          Next →
        </button>
      </div>
    `;
    
    listDiv.innerHTML += paginationHTML;
  }
  
  /**
   * Pagination navigation
   */
  function nextPage() {
    const totalPages = Math.ceil(state.filteredVideos.length / state.pageSize);
    if (state.currentPage < totalPages) {
      state.currentPage++;
      filterAndRenderPendingVideos();
    }
  }
  
  function prevPage() {
    if (state.currentPage > 1) {
      state.currentPage--;
      filterAndRenderPendingVideos();
    }
  }
  
  /**
   * Show linking modal with lesson search
   */
  async function showLinkingModal(videoId) {
    const video = state.pendingVideos.find(v => v.id === videoId);
    if (!video) {
      showError('Video not found');
      return;
    }
    
    // Create modal
    const modal = createLinkingModal(video);
    document.body.appendChild(modal);
    
    // Load lessons
    await loadLessonsForLinking(modal, video);
    
    // Setup close handlers
    const closeBtn = modal.querySelector('.close-modal');
    const cancelBtn = modal.querySelector('.cancel-link');
    
    const closeHandler = () => {
      modal.remove();
    };
    
    closeBtn.addEventListener('click', closeHandler);
    cancelBtn.addEventListener('click', closeHandler);
    
    // Click outside to close
    modal.addEventListener('click', function(e) {
      if (e.target === modal) {
        closeHandler();
      }
    });
  }
  
  /**
   * Create linking modal HTML
   */
  function createLinkingModal(video) {
    const modal = document.createElement('div');
    modal.className = 'link-modal';
    modal.innerHTML = `
      <div class="link-modal-content">
        <div class="link-modal-header">
          <h3>🔗 Link Video to Lesson</h3>
          <button class="close-modal">×</button>
        </div>
        <div class="link-modal-body">
          <div class="video-preview">
            <div class="preview-title">${escapeHtml(video.title)}</div>
            <div class="preview-meta">Season ${video.season || 'Unknown'} • ${(video.confidence_score * 100).toFixed(1)}% match</div>
          </div>
          
          <div class="lesson-search-section">
            <label for="lesson-search">Search Lessons</label>
            <input 
              type="text" 
              id="lesson-search" 
              placeholder="Type to search lessons..." 
              class="lesson-search-input"
            />
          </div>
          
          <div id="lessons-list" class="lessons-list">
            <div class="loading-lessons">Loading lessons...</div>
          </div>
        </div>
        <div class="link-modal-footer">
          <button class="cancel-link">Cancel</button>
          <button id="confirm-link-btn" class="confirm-link" disabled>Link to Selected Lesson</button>
        </div>
      </div>
    `;
    
    return modal;
  }
  
  /**
   * Load and display lessons for linking
   */
  async function loadLessonsForLinking(modal, video) {
    const listDiv = modal.querySelector('#lessons-list');
    const searchInput = modal.querySelector('#lesson-search');
    const confirmBtn = modal.querySelector('#confirm-link-btn');
    
    try {
      // Fetch all lessons (we'll filter client-side)
      const response = await fetch('/api/lessons');
      if (!response.ok) {
        throw new Error('Failed to load lessons');
      }
      
      const lessons = await response.json();
      console.log(`✅ Loaded ${lessons.length} lessons for linking`);
      
      let selectedLessonId = null;
      
      // Render lessons
      function renderLessons(filterText = '') {
        const filtered = lessons.filter(lesson => 
          lesson.title.toLowerCase().includes(filterText.toLowerCase())
        );
        
        if (filtered.length === 0) {
          listDiv.innerHTML = '<div class="no-lessons">No lessons found</div>';
          return;
        }
        
        listDiv.innerHTML = filtered.map(lesson => `
          <div class="lesson-option" data-lesson-id="${lesson.id}">
            <div class="lesson-option-title">${escapeHtml(lesson.title)}</div>
            <div class="lesson-option-meta">Course: ${lesson.course_id} • Order: ${lesson.order_index}</div>
          </div>
        `).join('');
        
        // Add click handlers
        modal.querySelectorAll('.lesson-option').forEach(option => {
          option.addEventListener('click', function() {
            modal.querySelectorAll('.lesson-option').forEach(o => o.classList.remove('selected'));
            option.classList.add('selected');
            selectedLessonId = option.dataset.lessonId;
            confirmBtn.disabled = false;
          });
        });
      }
      
      // Initial render
      renderLessons();
      
      // Search filter
      searchInput.addEventListener('input', function() {
        renderLessons(searchInput.value);
        selectedLessonId = null;
        confirmBtn.disabled = true;
      });
      
      // Confirm link button
      confirmBtn.addEventListener('click', async function() {
        if (!selectedLessonId) return;
        
        confirmBtn.disabled = true;
        confirmBtn.textContent = 'Linking...';
        
        try {
          await linkVideoToLesson(video.id, selectedLessonId);
          modal.remove();
          showSuccess('Video linked successfully!');
          
          // Immediately remove from state and re-render (optimistic update)
          state.pendingVideos = state.pendingVideos.filter(v => v.id !== video.id);
          filterAndRenderPendingVideos();
          
        } catch (error) {
          showError(`Linking failed: ${error.message}`);
          confirmBtn.disabled = false;
          confirmBtn.textContent = 'Link to Selected Lesson';
        }
      });
      
    } catch (error) {
      console.error('❌ Error loading lessons:', error);
      listDiv.innerHTML = `<div class="error-message">Error loading lessons: ${error.message}</div>`;
    }
  }
  
  /**
   * Link video to lesson via API
   */
  async function linkVideoToLesson(pendingId, lessonId) {
    console.log(`🔗 Linking video ${pendingId} to lesson ${lessonId}...`);
    
    const response = await fetch(`/api/youtube/link/${pendingId}/${lessonId}`, {
      method: 'POST'
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Linking failed');
    }
    
    const result = await response.json();
    console.log('✅ Link successful:', result);
    
    return result;
  }
  
  /**
   * Show error message
   */
  function showError(message) {
    const statusDiv = document.querySelector('#youtube-import-content .youtube-import-status') ||
                     createStatusDiv();
    statusDiv.className = 'youtube-import-status error';
    statusDiv.textContent = `❌ ${message}`;
    statusDiv.classList.remove('hidden');
    
    setTimeout(() => statusDiv.classList.add('hidden'), 5000);
  }
  
  /**
   * Show success message
   */
  function showSuccess(message) {
    const statusDiv = document.querySelector('#youtube-import-content .youtube-import-status') ||
                     createStatusDiv();
    statusDiv.className = 'youtube-import-status success';
    statusDiv.textContent = `✅ ${message}`;
    statusDiv.classList.remove('hidden');
    
    setTimeout(() => statusDiv.classList.add('hidden'), 5000);
  }
  
  /**
   * Create status div if it doesn't exist
   */
  function createStatusDiv() {
    const content = document.getElementById('youtube-import-content');
    const div = document.createElement('div');
    div.className = 'youtube-import-status hidden';
    content.insertBefore(div, content.firstChild);
    return div;
  }
  
  /**
   * Escape HTML to prevent XSS
   */
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
  
  // Expose API for pagination
  window.youtubeImport = {
    nextPage,
    prevPage
  };
  
  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initYouTubeImport);
  } else {
    initYouTubeImport();
  }
})();
