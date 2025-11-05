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

// ==== APPLICATION LOGIC ====

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', () => {
  // State
  let currentPage = 1;
  let currentSearch = '';
  const DOCS_PER_PAGE = 12;

  // Elements
  const searchInput = document.getElementById('search-input');
  const documentsGrid = document.getElementById('documents-grid');
  const paginationControls = document.getElementById('pagination-controls');
  const prevBtn = document.getElementById('prev-btn');
  const nextBtn = document.getElementById('next-btn');
  const paginationInfo = document.getElementById('pagination-info');
  const tagline = document.getElementById('tagline');

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

  // Initial load
  console.log('Content Atlas app initialized');
  console.log('Elements found:', {
    searchInput: !!searchInput,
    documentsGrid: !!documentsGrid,
    paginationControls: !!paginationControls,
    prevBtn: !!prevBtn,
    nextBtn: !!nextBtn,
    paginationInfo: !!paginationInfo,
    tagline: !!tagline
  });
  loadDocuments().catch(err => console.error('Initial load failed:', err));
});
