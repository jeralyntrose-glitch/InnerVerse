/**
 * MetadataTreeView - Vanilla JS component for rendering document metadata hierarchically
 * Displays structured metadata in organized sections with pills and proper formatting
 */

/**
 * Create a pill element
 * @param {string} text - Pill text content
 * @param {string} variant - Pill variant (default, small, etc)
 * @returns {HTMLElement}
 */
function createPill(text, variant = 'default') {
  const pill = document.createElement('span');
  pill.className = `metadata-pill ${variant}`;
  pill.textContent = text || 'N/A';
  return pill;
}

/**
 * Create a metadata row
 * @param {string} label - Row label
 * @param {string|Array} value - Value(s) to display
 * @returns {HTMLElement}
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
 * @param {string} title - Section title (with emoji)
 * @param {Array<HTMLElement>} rows - Metadata rows
 * @returns {HTMLElement}
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
 * @param {Object} data - Document data
 * @param {Object} data.metadata - Structured metadata object
 * @param {string} data.title - Document title
 * @param {string} data.upload_date - Upload date
 * @returns {HTMLElement}
 */
export function renderMetadataTreeView(data) {
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
 * @param {Array<Object>} documents - Array of document data
 * @param {HTMLElement} containerElement - Target container
 */
export function renderDocumentGrid(documents, containerElement) {
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
