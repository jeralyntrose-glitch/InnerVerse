/**
 * Content Atlas Application
 * Handles fetching and rendering documents with structured metadata
 */

// ==== METADATA TREE VIEW RENDERING ====

/**
 * Create a pill element
 */
function createPill(text, variant = 'default') {
  const pill = document.createElement('span');
  pill.className = `metadata-pill ${variant}`;
  pill.textContent = text || 'N/A';
  return pill;
}

/**
 * Create a metadata row
 */
function createMetadataRow(label, value) {
  const row = document.createElement('div');
  row.className = 'metadata-row';
  
  const labelSpan = document.createElement('span');
  labelSpan.className = 'metadata-label';
  labelSpan.textContent = label;
  
  const valueContainer = document.createElement('div');
  valueContainer.className = 'metadata-value';
  
  // Handle arrays
  if (Array.isArray(value)) {
    if (value.length === 0) {
      valueContainer.appendChild(createPill('N/A', 'na'));
    } else {
      const pillGroup = document.createElement('div');
      pillGroup.className = 'pill-group';
      value.forEach(item => {
        pillGroup.appendChild(createPill(item));
      });
      valueContainer.appendChild(pillGroup);
    }
  } else {
    // Handle single values
    const displayValue = value || 'N/A';
    const pillVariant = (!value || value === 'N/A' || value === 'n/a' || value === 'none' || value === 'unknown') ? 'na' : 'default';
    valueContainer.appendChild(createPill(displayValue, pillVariant));
  }
  
  row.appendChild(labelSpan);
  row.appendChild(valueContainer);
  
  return row;
}

/**
 * Create a metadata section
 */
function createMetadataSection(title, rows) {
  const section = document.createElement('section');
  section.className = 'metadata-section';
  
  const heading = document.createElement('h4');
  heading.className = 'section-heading';
  heading.textContent = title;
  
  section.appendChild(heading);
  rows.forEach(row => section.appendChild(row));
  
  return section;
}

/**
 * Render a complete metadata tree view
 */
function renderMetadataTreeView(data) {
  const { metadata, title, upload_date } = data;
  
  const container = document.createElement('div');
  container.className = 'metadata-tree-view';
  
  // Header
  const heading = document.createElement('h3');
  heading.className = 'document-title';
  heading.textContent = title || 'Untitled Document';
  
  const dateSpan = document.createElement('p');
  dateSpan.className = 'upload-date';
  dateSpan.textContent = upload_date && upload_date !== 'unknown' 
    ? `Uploaded: ${upload_date}` 
    : 'Upload date unknown';
  
  container.appendChild(heading);
  container.appendChild(dateSpan);
  
  // Content Structure Section
  const contentRows = [
    createMetadataRow('Type:', metadata.content_type),
    createMetadataRow('Level:', metadata.difficulty),
    createMetadataRow('Focus:', metadata.primary_category)
  ];
  container.appendChild(createMetadataSection('📑 Content Structure', contentRows));
  
  // Personality Framework Section
  const personalityRows = [
    createMetadataRow('Types:', metadata.types_discussed || []),
    createMetadataRow('Functions:', metadata.functions_covered || []),
    createMetadataRow('Quadra:', metadata.quadra),
    createMetadataRow('Temple:', metadata.temple)
  ];
  container.appendChild(createMetadataSection('👤 Personality Framework', personalityRows));
  
  // Relationships Section
  const relationshipRows = [
    createMetadataRow('Context:', metadata.relationship_type)
  ];
  container.appendChild(createMetadataSection('💕 Relationships', relationshipRows));
  
  // Content Themes Section
  const themesRows = [
    createMetadataRow('Topics:', metadata.topics || [])
  ];
  container.appendChild(createMetadataSection('📚 Content Themes', themesRows));
  
  // Practical Application Section
  const applicationRows = [
    createMetadataRow('Use For:', metadata.use_case || [])
  ];
  container.appendChild(createMetadataSection('💡 Practical Application', applicationRows));
  
  return container;
}

/**
 * Render multiple documents in a grid
 */
function renderDocumentGrid(documents, containerElement) {
  containerElement.innerHTML = '';
  
  if (!documents || documents.length === 0) {
    const emptyMessage = document.createElement('div');
    emptyMessage.className = 'empty-state';
    emptyMessage.innerHTML = `
      <p style="font-size: 18px; color: var(--text-secondary); margin: 60px 0;">
        🗺️ No documents found
      </p>
    `;
    containerElement.appendChild(emptyMessage);
    return;
  }
  
  documents.forEach(doc => {
    const treeView = renderMetadataTreeView(doc);
    containerElement.appendChild(treeView);
  });
}

// ==== FILTER SIDEBAR LOGIC ====

/**
 * Render a collapsible filter section
 */
function renderFilterSection(title, filterKey, options, activeFilters, icon = '📊') {
  const section = document.createElement('div');
  section.className = 'filter-section';
  
  const header = document.createElement('div');
  header.className = 'filter-section-header';
  header.innerHTML = `
    <span>${icon} ${title}</span>
    <span class="filter-toggle">▼</span>
  `;
  
  const content = document.createElement('div');
  content.className = 'filter-section-content';
  
  // Add "Select All" and "Clear" buttons if more than 3 options
  if (options.length > 3) {
    const controls = document.createElement('div');
    controls.className = 'filter-controls';
    controls.innerHTML = `
      <button class="filter-control-btn select-all-btn" data-filter="${filterKey}">Select All</button>
      <button class="filter-control-btn clear-btn" data-filter="${filterKey}">Clear</button>
    `;
    content.appendChild(controls);
  }
  
  // Add checkboxes
  const checkboxes = document.createElement('div');
  checkboxes.className = 'filter-checkboxes';
  
  options.forEach(option => {
    const label = document.createElement('label');
    label.className = 'filter-checkbox-label';
    
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.value = option;
    checkbox.dataset.filterKey = filterKey;
    checkbox.checked = activeFilters[filterKey]?.includes(option) || false;
    
    const span = document.createElement('span');
    span.textContent = option;
    
    label.appendChild(checkbox);
    label.appendChild(span);
    checkboxes.appendChild(label);
  });
  
  content.appendChild(checkboxes);
  
  // Collapse toggle
  header.addEventListener('click', () => {
    content.classList.toggle('collapsed');
    const toggle = header.querySelector('.filter-toggle');
    toggle.textContent = content.classList.contains('collapsed') ? '▶' : '▼';
  });
  
  section.appendChild(header);
  section.appendChild(content);
  
  return section;
}

/**
 * Render all filter sections
 */
function renderFilterSidebar(filterOptions, activeFilters) {
  const filterSectionsContainer = document.getElementById('filter-sections');
  filterSectionsContainer.innerHTML = '';
  
  const sections = [
    { title: 'Content Type', key: 'content_type', icon: '📑', options: filterOptions.content_types || [] },
    { title: 'Difficulty', key: 'difficulty', icon: '📊', options: filterOptions.difficulties || [] },
    { title: 'Category', key: 'primary_category', icon: '🎯', options: filterOptions.primary_categories || [] },
    { title: 'MBTI Types', key: 'types_discussed', icon: '👤', options: filterOptions.types_discussed || [] },
    { title: 'Cognitive Functions', key: 'functions_covered', icon: '⚙️', options: filterOptions.functions_covered || [] },
    { title: 'Quadra', key: 'quadra', icon: '🔷', options: filterOptions.quadras || [] },
    { title: 'Temple', key: 'temple', icon: '🏛️', options: filterOptions.temples || [] },
    { title: 'Relationship Type', key: 'relationship_type', icon: '💕', options: filterOptions.relationship_types || [] },
    { title: 'Topics', key: 'topics', icon: '📚', options: filterOptions.topics || [] },
    { title: 'Use Cases', key: 'use_case', icon: '💡', options: filterOptions.use_cases || [] }
  ];
  
  sections.forEach(({ title, key, icon, options }) => {
    if (options.length > 0) {
      const section = renderFilterSection(title, key, options, activeFilters, icon);
      filterSectionsContainer.appendChild(section);
    }
  });
}

/**
 * Count active filters
 */
function countActiveFilters(activeFilters) {
  let count = 0;
  for (const key in activeFilters) {
    if (activeFilters[key] && activeFilters[key].length > 0) {
      count += activeFilters[key].length;
    }
  }
  return count;
}

/**
 * Update filter count badge
 */
function updateFilterBadge(activeFilters) {
  const badge = document.getElementById('filter-count-badge');
  const count = countActiveFilters(activeFilters);
  
  if (count > 0) {
    badge.textContent = count;
    badge.classList.remove('hidden');
  } else {
    badge.classList.add('hidden');
  }
}

// ==== APPLICATION LOGIC ====

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', () => {
  // State
  let currentPage = 1;
  let currentSearch = '';
  let activeFilters = {
    content_type: [],
    difficulty: [],
    primary_category: [],
    types_discussed: [],
    functions_covered: [],
    relationship_type: [],
    quadra: [],
    temple: [],
    topics: [],
    use_case: []
  };
  let filterOptions = null;
  const DOCS_PER_PAGE = 12;

  // Elements
  const searchInput = document.getElementById('search-input');
  const documentsGrid = document.getElementById('documents-grid');
  const paginationControls = document.getElementById('pagination-controls');
  const prevBtn = document.getElementById('prev-btn');
  const nextBtn = document.getElementById('next-btn');
  const paginationInfo = document.getElementById('pagination-info');
  const tagline = document.getElementById('tagline');
  const filterSidebar = document.getElementById('filter-sidebar');
  const mobileFilterToggle = document.getElementById('mobile-filter-toggle');
  const closeSidebarBtn = document.getElementById('close-sidebar');
  const clearAllFiltersBtn = document.getElementById('clear-all-filters');
  const filterSectionsContainer = document.getElementById('filter-sections');

  // Fetch filter options from API
  async function loadFilterOptions() {
    try {
      console.log('Fetching filter options...');
      const response = await fetch('/api/content-atlas/filters');
      if (!response.ok) {
        throw new Error(`Failed to fetch filters: ${response.status}`);
      }
      filterOptions = await response.json();
      console.log('Filter options loaded:', filterOptions);
      
      // Render filter sidebar
      renderFilterSidebar(filterOptions, activeFilters);
      
      // Attach event listeners to filter checkboxes
      attachFilterEventListeners();
      
    } catch (error) {
      console.error('Error loading filter options:', error);
      document.getElementById('filter-sections').innerHTML = `
        <div style="padding: 20px; text-align: center; color: var(--text-secondary);">
          Failed to load filters
        </div>
      `;
    }
  }

  // Fetch and render documents
  async function loadDocuments() {
    try {
      // Show loading state
      documentsGrid.innerHTML = `
        <div class="loading-state">
          <div class="loading-spinner"></div>
          <p style="margin-top: 20px; color: var(--text-secondary);">Loading documents...</p>
        </div>
      `;
      paginationControls.style.display = 'none';

      // Build API URL
      const params = new URLSearchParams({
        page: currentPage,
        limit: DOCS_PER_PAGE
      });
      
      if (currentSearch.trim()) {
        params.append('search', currentSearch.trim());
      }

      // Add filters if any are active
      if (countActiveFilters(activeFilters) > 0) {
        params.append('filters', JSON.stringify(activeFilters));
      }

      console.log('Fetching:', `/api/content-atlas?${params}`);
      const response = await fetch(`/api/content-atlas?${params}`);
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      console.log('Data received:', {
        documentCount: data.documents?.length,
        totalDocs: data.pagination?.total_documents
      });
      
      // Render documents
      console.log('Starting render...');
      renderDocumentGrid(data.documents, documentsGrid);
      console.log('Render complete!');

      // Update pagination
      updatePagination(data.pagination);

      // Update tagline
      const totalDocs = data.pagination.total_documents;
      const searchText = currentSearch.trim() ? ` matching "${currentSearch.trim()}"` : '';
      tagline.textContent = `Explore ${totalDocs} documents${searchText}`;

    } catch (error) {
      console.error('Error loading documents:', error);
      documentsGrid.innerHTML = `
        <div class="empty-state">
          <p style="font-size: 18px; color: var(--text-secondary);">
            ❌ Error loading documents: ${error.message}
          </p>
          <button onclick="location.reload()" class="pagination-btn" style="margin-top: 20px;">
            Retry
          </button>
        </div>
      `;
    }
  }

  // Update pagination controls
  function updatePagination(pagination) {
    if (pagination.total_pages <= 1) {
      paginationControls.style.display = 'none';
      return;
    }

    paginationControls.style.display = 'flex';
    
    prevBtn.disabled = !pagination.has_previous;
    nextBtn.disabled = !pagination.has_next;
    
    paginationInfo.textContent = `Page ${pagination.page} of ${pagination.total_pages} (${pagination.total_documents} total)`;
  }

  // Event listeners
  prevBtn.addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage--;
      loadDocuments();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  });

  nextBtn.addEventListener('click', () => {
    currentPage++;
    loadDocuments();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  // Search with debounce
  let searchTimeout;
  searchInput.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      currentSearch = e.target.value;
      currentPage = 1; // Reset to first page
      loadDocuments();
    }, 500); // 500ms debounce
  });

  // Filter event handlers
  let filterTimeout;
  function attachFilterEventListeners() {
    // Handle checkbox changes with debounce
    filterSectionsContainer.addEventListener('change', (e) => {
      if (e.target.type === 'checkbox') {
        const filterKey = e.target.dataset.filterKey;
        const value = e.target.value;
        const checked = e.target.checked;
        
        // Update activeFilters
        if (checked) {
          if (!activeFilters[filterKey].includes(value)) {
            activeFilters[filterKey].push(value);
          }
        } else {
          activeFilters[filterKey] = activeFilters[filterKey].filter(v => v !== value);
        }
        
        // Update Clear All button visibility
        updateClearAllButton();
        
        // Update filter badge
        updateFilterBadge(activeFilters);
        
        // Debounce document reload
        clearTimeout(filterTimeout);
        filterTimeout = setTimeout(() => {
          currentPage = 1; // Reset to first page
          loadDocuments();
        }, 300); // 300ms debounce
      }
    });
    
    // Handle Select All / Clear buttons
    filterSectionsContainer.addEventListener('click', (e) => {
      if (e.target.classList.contains('select-all-btn')) {
        const filterKey = e.target.dataset.filter;
        const section = e.target.closest('.filter-section');
        const checkboxes = section.querySelectorAll('input[type="checkbox"]');
        
        checkboxes.forEach(checkbox => {
          if (!checkbox.checked) {
            checkbox.checked = true;
            const value = checkbox.value;
            if (!activeFilters[filterKey].includes(value)) {
              activeFilters[filterKey].push(value);
            }
          }
        });
        
        updateClearAllButton();
        updateFilterBadge(activeFilters);
        currentPage = 1;
        loadDocuments();
      }
      
      if (e.target.classList.contains('clear-btn')) {
        const filterKey = e.target.dataset.filter;
        const section = e.target.closest('.filter-section');
        const checkboxes = section.querySelectorAll('input[type="checkbox"]');
        
        checkboxes.forEach(checkbox => {
          checkbox.checked = false;
        });
        
        activeFilters[filterKey] = [];
        updateClearAllButton();
        updateFilterBadge(activeFilters);
        currentPage = 1;
        loadDocuments();
      }
    });
  }

  // Update Clear All button visibility
  function updateClearAllButton() {
    if (countActiveFilters(activeFilters) > 0) {
      clearAllFiltersBtn.style.display = 'inline-block';
    } else {
      clearAllFiltersBtn.style.display = 'none';
    }
  }

  // Clear all filters
  clearAllFiltersBtn.addEventListener('click', () => {
    // Reset all filters
    for (const key in activeFilters) {
      activeFilters[key] = [];
    }
    
    // Uncheck all checkboxes
    const allCheckboxes = filterSectionsContainer.querySelectorAll('input[type="checkbox"]');
    allCheckboxes.forEach(checkbox => {
      checkbox.checked = false;
    });
    
    updateClearAllButton();
    updateFilterBadge(activeFilters);
    currentPage = 1;
    loadDocuments();
  });

  // Mobile filter sidebar toggle
  mobileFilterToggle.addEventListener('click', () => {
    filterSidebar.classList.toggle('active');
  });

  closeSidebarBtn.addEventListener('click', () => {
    filterSidebar.classList.remove('active');
  });

  // Close sidebar when clicking outside on mobile
  document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768) {
      if (!filterSidebar.contains(e.target) && !mobileFilterToggle.contains(e.target)) {
        filterSidebar.classList.remove('active');
      }
    }
  });

  // Initial load
  console.log('Content Atlas app initialized');
  console.log('Elements found:', {
    searchInput: !!searchInput,
    documentsGrid: !!documentsGrid,
    paginationControls: !!paginationControls,
    prevBtn: !!prevBtn,
    nextBtn: !!nextBtn,
    paginationInfo: !!paginationInfo,
    tagline: !!tagline,
    filterSidebar: !!filterSidebar,
    mobileFilterToggle: !!mobileFilterToggle
  });
  
  // Load filters first, then load documents
  loadFilterOptions()
    .then(() => loadDocuments())
    .catch(err => console.error('Initial load failed:', err));
});
