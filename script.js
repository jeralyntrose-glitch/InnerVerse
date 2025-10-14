const dropArea = document.getElementById('drop-area');
const fileInput = document.getElementById('fileElem');
const gdriveBtn = document.getElementById('gdrive-btn');
const status = document.getElementById('status');
const chatToggle = document.getElementById('chat-toggle');
const chatContainer = document.getElementById('chat-container');
const chatClose = document.getElementById('chat-close');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const chatLog = document.getElementById('chat-log');

// Theme toggle
const themeToggle = document.getElementById('theme-toggle');
const sunIcon = themeToggle.querySelector('.sun-icon');
const moonIcon = themeToggle.querySelector('.moon-icon');

// Load saved theme
const savedTheme = localStorage.getItem('theme') || 'light';
document.documentElement.setAttribute('data-theme', savedTheme);
if (savedTheme === 'dark') {
  sunIcon.classList.add('hidden');
  moonIcon.classList.remove('hidden');
}

// Theme toggle handler
themeToggle.addEventListener('click', () => {
  const currentTheme = document.documentElement.getAttribute('data-theme');
  const newTheme = currentTheme === 'light' ? 'dark' : 'light';
  
  document.documentElement.setAttribute('data-theme', newTheme);
  localStorage.setItem('theme', newTheme);
  
  // Toggle icons
  if (newTheme === 'dark') {
    sunIcon.classList.add('hidden');
    moonIcon.classList.remove('hidden');
  } else {
    sunIcon.classList.remove('hidden');
    moonIcon.classList.add('hidden');
  }
});

// Dropdown elements
const dropdownToggle = document.getElementById('dropdown-toggle');
const dropdownMenu = document.getElementById('dropdown-menu');
const docList = document.getElementById('doc-list');
const copyAllBtn = document.getElementById('copy-all-btn');
const viewArchiveBtn = document.getElementById('view-archive-btn');

// Archive modal
const archiveModal = document.getElementById('archive-modal');
const closeArchiveBtn = document.getElementById('archive-close');
const archiveList = document.getElementById('archive-list');

// Ensure modal starts hidden
if (archiveModal) {
  archiveModal.classList.add('hidden');
}

let currentDocumentId = null;

// === Persistent Storage ===
const STORAGE_KEY = 'axis_mind_uploads';
const ARCHIVE_KEY = 'axis_mind_archive';

function loadUploadedFiles() {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored ? JSON.parse(stored) : [];
}

function saveUploadedFiles(files) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(files));
}

function loadArchive() {
  const stored = localStorage.getItem(ARCHIVE_KEY);
  return stored ? JSON.parse(stored) : [];
}

function saveArchive(files) {
  localStorage.setItem(ARCHIVE_KEY, JSON.stringify(files));
}

function cleanExpiredArchive() {
  const archive = loadArchive();
  const now = Date.now();
  const filtered = archive.filter(entry => (now - entry.timestamp) < 30 * 24 * 60 * 60 * 1000);
  saveArchive(filtered);
  return filtered;
}

// === Upload ===
let uploadedFiles = loadUploadedFiles();
const uploadStatusSection = document.getElementById('upload-status-section');
const uploadList = document.getElementById('upload-list');
const countUploaded = document.getElementById('count-uploaded');
const countCompleted = document.getElementById('count-completed');
const countErrors = document.getElementById('count-errors');
const cancelUploadBtn = document.getElementById('cancel-upload-btn');

let uploadStats = { uploaded: 0, completed: 0, errors: 0 };
let activeUploads = []; // Track active uploads for cancellation
let uploadsCancelled = false; // Global flag to stop upload loops

['dragenter', 'dragover'].forEach(event => {
  dropArea.addEventListener(event, e => {
    e.preventDefault();
    dropArea.classList.add('dragover');
  });
});

['dragleave', 'drop'].forEach(event => {
  dropArea.addEventListener(event, e => {
    e.preventDefault();
    dropArea.classList.remove('dragover');
  });
});

dropArea.addEventListener('drop', e => {
  const files = Array.from(e.dataTransfer.files);
  handleFiles(files);
});

fileInput.addEventListener('change', e => {
  const files = Array.from(e.target.files);
  handleFiles(files);
});

function handleFiles(files) {
  const pdfFiles = files.filter(f => f.type === 'application/pdf');
  
  if (pdfFiles.length === 0) {
    status.textContent = '❌ Please upload valid PDF file(s).';
    return;
  }

  // Reset stats and show upload section
  uploadStats = { uploaded: pdfFiles.length, completed: 0, errors: 0 };
  activeUploads = []; // Clear previous uploads
  uploadsCancelled = false; // Reset cancellation flag
  updateStats();
  uploadStatusSection.classList.remove('hidden');
  uploadList.innerHTML = '';
  status.textContent = '';
  cancelUploadBtn.classList.remove('hidden'); // Show cancel button

  // Process each file
  pdfFiles.forEach(file => {
    processFile(file);
  });
}

function updateStats() {
  countUploaded.textContent = uploadStats.uploaded;
  countCompleted.textContent = uploadStats.completed;
  countErrors.textContent = uploadStats.errors;
}

function processFile(file) {
  // Create upload item
  const itemId = `upload-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  const uploadItem = document.createElement('div');
  uploadItem.className = 'upload-item';
  uploadItem.id = itemId;
  uploadItem.innerHTML = `
    <div class="upload-filename">${file.name}</div>
    <div class="progress-bar-container">
      <div class="progress-bar"></div>
    </div>
  `;
  uploadList.appendChild(uploadItem);

  const progressBar = uploadItem.querySelector('.progress-bar');

  // Create AbortController for this upload
  const abortController = new AbortController();
  activeUploads.push({ itemId, abortController, progressBar, uploadItem });
  
  // Ensure cancel button is visible when there are active uploads
  if (activeUploads.length > 0) {
    cancelUploadBtn.classList.remove('hidden');
  }

  // Simulate progress while reading file
  let progress = 0;
  const progressInterval = setInterval(() => {
    progress += 10;
    if (progress <= 50) {
      progressBar.style.width = `${progress}%`;
    }
  }, 100);

  // Check for duplicates
  if (uploadedFiles.find(f => f.name === file.name)) {
    const replace = confirm(`"${file.name}" already uploaded. Replace it?`);
    if (!replace) {
      clearInterval(progressInterval);
      uploadItem.classList.add('error');
      progressBar.style.width = '100%';
      uploadStats.errors++;
      updateStats();
      // Remove from active uploads
      activeUploads = activeUploads.filter(u => u.itemId !== itemId);
      checkUploadComplete();
      return;
    }
  }

  const reader = new FileReader();
  reader.onload = async () => {
    clearInterval(progressInterval);
    progressBar.style.width = '60%';

    const base64Data = reader.result.split(',')[1];
    const payload = { filename: file.name, pdf_base64: base64Data };

    try {
      const res = await fetch('/upload-base64', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: abortController.signal
      });

      progressBar.style.width = '80%';

      const result = await res.json();

      if (res.ok) {
        currentDocumentId = result.document_id;

        uploadedFiles = uploadedFiles.filter(f => f.name !== file.name);
        uploadedFiles.push({ 
          name: file.name, 
          id: result.document_id,
          timestamp: Date.now()
        });
        saveUploadedFiles(uploadedFiles);
        updateDropdown();

        // Success
        progressBar.style.width = '100%';
        uploadItem.classList.add('success');
        uploadStats.completed++;
        updateStats();

        // Copy first successful document ID
        if (uploadStats.completed === 1) {
          navigator.clipboard.writeText(result.document_id);
        }
      } else {
        throw new Error(result.error || 'Upload failed.');
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        // Upload was cancelled
        uploadItem.classList.add('error');
        uploadItem.querySelector('.upload-filename').textContent = `${file.name} (Cancelled)`;
      } else {
        progressBar.style.width = '100%';
        uploadItem.classList.add('error');
        uploadStats.errors++;
        updateStats();
      }
    } finally {
      // Remove from active uploads
      activeUploads = activeUploads.filter(u => u.itemId !== itemId);
      checkUploadComplete();
    }
  };

  reader.readAsDataURL(file);
}

// Check if all uploads are complete and hide cancel button
function checkUploadComplete() {
  if (activeUploads.length === 0) {
    cancelUploadBtn.classList.add('hidden');
  }
}

// Cancel all active uploads
function cancelAllUploads() {
  uploadsCancelled = true; // Set flag to stop upload loops
  activeUploads.forEach(upload => {
    upload.abortController.abort();
    upload.uploadItem.classList.add('error');
    upload.progressBar.style.width = '100%';
  });
  activeUploads = [];
  cancelUploadBtn.classList.add('hidden');
}

// Cancel button event listener
cancelUploadBtn.addEventListener('click', () => {
  if (confirm('Cancel all ongoing uploads?')) {
    cancelAllUploads();
  }
});

// === Google Drive Integration ===
let pickerApiLoaded = false;
let googleApiKey = null;
let accessToken = null;

// Load Google Picker API
function loadPickerApi() {
  gapi.load('picker', {
    callback: () => {
      pickerApiLoaded = true;
      console.log('✅ Google Picker API loaded');
    },
    onerror: () => {
      console.error('❌ Failed to load Google Picker API');
    }
  });
}

// Initialize on page load
if (typeof gapi !== 'undefined') {
  loadPickerApi();
} else {
  window.addEventListener('load', () => {
    setTimeout(loadPickerApi, 500);
  });
}

// Open Google Drive Picker
gdriveBtn.addEventListener('click', async () => {
  try {
    // Check if Picker API is loaded
    if (!pickerApiLoaded) {
      alert('⏳ Google Drive is still loading. Please wait a moment and try again.');
      loadPickerApi();
      return;
    }

    // Get API key and access token
    const [apiKeyResponse, tokenResponse] = await Promise.all([
      fetch('/api/google-api-key'),
      fetch('/api/gdrive-token')
    ]);

    const apiKeyData = await apiKeyResponse.json();
    const tokenData = await tokenResponse.json();

    if (!apiKeyData.api_key || !tokenData.access_token) {
      alert('❌ Google Drive not properly configured. Please contact support.');
      return;
    }

    googleApiKey = apiKeyData.api_key;
    accessToken = tokenData.access_token;

    // Replit runs in an iframe, so we need to use the parent origin
    const pickerOrigin = 'https://replit.com';
    
    console.log('🔑 API Key present:', !!googleApiKey);
    console.log('🎫 Access Token present:', !!accessToken);
    console.log('🌐 Picker origin:', pickerOrigin);

    // Create and show the picker
    const picker = new google.picker.PickerBuilder()
      .addView(
        new google.picker.DocsView(google.picker.ViewId.DOCS)
          .setMimeTypes('application/pdf')
          .setIncludeFolders(true)
      )
      .setOAuthToken(accessToken)
      // Try without API key first - often works better
      // .setDeveloperKey(googleApiKey)
      .setCallback(pickerCallback)
      .setOrigin(pickerOrigin)
      .setTitle('Select PDF files from Google Drive')
      .enableFeature(google.picker.Feature.MULTISELECT_ENABLED)
      .build();

    console.log('✅ Picker built, showing now...');
    picker.setVisible(true);
  } catch (error) {
    console.error('Picker error:', error);
    alert('❌ Failed to open Google Drive picker: ' + error.message);
  }
});

// Handle picker selection
async function pickerCallback(data) {
  if (data.action === google.picker.Action.PICKED) {
    const files = data.docs.filter(doc => doc.mimeType === 'application/pdf');
    
    if (files.length === 0) {
      alert('❌ Please select PDF files only.');
      return;
    }

    // Setup upload tracking
    uploadStats = { uploaded: files.length, completed: 0, errors: 0 };
    activeUploads = [];
    uploadsCancelled = false;
    updateStats();
    uploadStatusSection.classList.remove('hidden');
    uploadList.innerHTML = '';
    status.textContent = '';
    cancelUploadBtn.classList.remove('hidden');

    // Download and process each file
    for (const file of files) {
      if (uploadsCancelled) break;
      await downloadAndProcessGDriveFile(file.id, file.name);
    }

    // Hide cancel button if all done
    if (activeUploads.length === 0 && !uploadsCancelled) {
      cancelUploadBtn.classList.add('hidden');
    }
  }
}

async function downloadAndProcessGDriveFile(fileId, fileName) {
  // Create upload item for tracking
  const itemId = `gdrive-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  const uploadItem = document.createElement('div');
  uploadItem.className = 'upload-item';
  uploadItem.id = itemId;
  uploadItem.innerHTML = `
    <div class="upload-filename">${fileName}</div>
    <div class="progress-bar-container">
      <div class="progress-bar"></div>
    </div>
  `;
  uploadList.appendChild(uploadItem);
  
  const progressBar = uploadItem.querySelector('.progress-bar');
  progressBar.style.width = '30%';
  
  // Create AbortController for this upload
  const abortController = new AbortController();
  activeUploads.push({ itemId, abortController, progressBar, uploadItem });
  
  // Ensure cancel button is visible when there are active uploads
  if (activeUploads.length > 0) {
    cancelUploadBtn.classList.remove('hidden');
  }
  
  try {
    // Download from Google Drive
    const response = await fetch(`/api/gdrive-download/${fileId}`, {
      signal: abortController.signal
    });
    progressBar.style.width = '60%';
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || 'Download failed');
    }
    
    // Upload to backend
    const payload = { filename: fileName, pdf_base64: data.pdf_base64 };
    const uploadResponse = await fetch('/upload-base64', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: abortController.signal
    });
    
    progressBar.style.width = '80%';
    const result = await uploadResponse.json();
    
    if (uploadResponse.ok) {
      currentDocumentId = result.document_id;
      
      uploadedFiles = uploadedFiles.filter(f => f.name !== fileName);
      uploadedFiles.push({ 
        name: fileName, 
        id: result.document_id,
        timestamp: Date.now()
      });
      saveUploadedFiles(uploadedFiles);
      updateDropdown();
      
      // Success
      progressBar.style.width = '100%';
      uploadItem.classList.add('success');
      uploadStats.completed++;
      updateStats();
      
      if (uploadStats.completed === 1) {
        navigator.clipboard.writeText(result.document_id);
      }
    } else {
      throw new Error(result.error || 'Upload failed');
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      // Upload was cancelled
      uploadItem.classList.add('error');
      uploadItem.querySelector('.upload-filename').textContent = `${fileName} (Cancelled)`;
    } else {
      console.error('GDrive file error:', error);
      progressBar.style.width = '100%';
      uploadItem.classList.add('error');
      uploadStats.errors++;
      updateStats();
    }
  } finally {
    // Remove from active uploads
    activeUploads = activeUploads.filter(u => u.itemId !== itemId);
    checkUploadComplete();
  }
}

// === Chat ===
chatToggle.addEventListener('click', () => {
  chatContainer.classList.toggle('hidden');
});

chatClose.addEventListener('click', () => {
  chatContainer.classList.add('hidden');
});

sendBtn.addEventListener('click', sendMessage);
chatInput.addEventListener('keypress', e => {
  if (e.key === 'Enter') sendMessage();
});

async function sendMessage() {
  const question = chatInput.value.trim();
  if (!question) return;

  if (!currentDocumentId) {
    appendMessage('bot', '⚠️ Please upload a PDF first.');
    return;
  }

  appendMessage('user', question);
  appendMessage('bot', '🧠 Thinking...');
  sendBtn.disabled = true;

  try {
    const res = await fetch('/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_id: currentDocumentId, question })
    });

    const data = await res.json();
    removeLastBotMessage();

    if (res.ok) {
      appendMessage('bot', data.answer || 'No response.');
    } else {
      appendMessage('bot', `❌ Error: ${data.error || 'Query failed.'}`);
    }
  } catch (err) {
    removeLastBotMessage();
    appendMessage('bot', `❌ Error: ${err.message}`);
  }

  sendBtn.disabled = false;
  chatInput.value = '';
}

function appendMessage(sender, text) {
  const message = document.createElement('div');
  message.classList.add('chat-message', sender);
  message.textContent = text;
  chatLog.appendChild(message);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function removeLastBotMessage() {
  const messages = chatLog.querySelectorAll('.chat-message.bot');
  if (messages.length > 0) messages[messages.length - 1].remove();
}

// === Dropdown & Archive ===
dropdownToggle.addEventListener('click', (e) => {
  e.stopPropagation(); // Prevent document click from firing
  const isHidden = dropdownMenu.classList.contains('hidden');
  if (isHidden) {
    dropdownMenu.classList.remove('hidden');
    updateDropdown();
  } else {
    dropdownMenu.classList.add('hidden');
  }
});

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
  if (!dropdownMenu.contains(e.target) && !dropdownToggle.contains(e.target)) {
    dropdownMenu.classList.add('hidden');
  }
});

function updateDropdown() {
  docList.innerHTML = '';

  uploadedFiles.forEach(file => {
    const li = document.createElement('li');
    const date = file.timestamp ? new Date(file.timestamp).toLocaleString() : 'Unknown';
    const shortId = file.id ? (file.id.substring(0, 8) + '...') : 'No ID';
    const fullId = file.id || 'unknown';
    
    li.innerHTML = `
      <input type="checkbox" class="doc-checkbox" data-id="${fullId}">
      <div class="doc-info">
        <div class="doc-name" title="${file.name}">${file.name}</div>
        <div class="doc-meta">
          <span class="doc-id" title="${fullId}">ID: ${shortId}</span>
          <span class="doc-date">${date}</span>
        </div>
      </div>
      <div class="doc-actions">
        <button class="copy-btn" data-id="${fullId}" title="Copy">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
        </button>
        <button class="delete-btn" data-id="${fullId}" title="Delete">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </div>
    `;
    docList.appendChild(li);
  });

  docList.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.dataset.id;
      const file = uploadedFiles.find(f => f.id === id);
      if (!file) {
        navigator.clipboard.writeText(id);
        alert('📋 Document ID copied!');
        return;
      }
      
      // Format timestamp as readable date/time
      const date = file.timestamp ? new Date(file.timestamp).toLocaleString() : 'N/A';
      
      // Tab-separated format for Google Sheets: Filename\tID\tTimestamp
      const tsvData = `${file.name}\t${file.id}\t${date}`;
      
      navigator.clipboard.writeText(tsvData);
      alert('📋 Document info copied! (Filename, ID, date)');
    });
  });

  docList.querySelectorAll('.delete-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.dataset.id;
      const file = uploadedFiles.find(f => f.id === id);
      if (!file) return;

      const confirmed = confirm(`Archive "${file.name}" for 30 days?`);
      if (confirmed) {
        uploadedFiles = uploadedFiles.filter(f => f.id !== id);
        saveUploadedFiles(uploadedFiles);

        const archive = cleanExpiredArchive();
        archive.push({ name: file.name, id: file.id, timestamp: Date.now() });
        saveArchive(archive);
        updateDropdown();
      }
    });
  });
}

// === Copy Selected Button ===
const copySelectedBtn = document.getElementById('copy-selected-btn');
copySelectedBtn.addEventListener('click', () => {
  const checkboxes = document.querySelectorAll('.doc-checkbox:checked');
  
  if (checkboxes.length === 0) {
    alert('No documents selected! Please check the boxes next to the files you want to copy.');
    return;
  }
  
  const selectedIds = Array.from(checkboxes).map(cb => cb.dataset.id);
  const selectedFiles = uploadedFiles.filter(file => selectedIds.includes(file.id));
  
  const tsvData = selectedFiles
    .map(file => {
      const date = file.timestamp ? new Date(file.timestamp).toLocaleString() : 'N/A';
      return `${file.name}\t${file.id}\t${date}`;
    })
    .join('\n');
  
  if (tsvData) {
    navigator.clipboard.writeText(tsvData);
    alert(`📋 Copied ${selectedFiles.length} selected document(s)! (Filename, ID, date)\nPaste into Google Sheets - each part will go into a separate column.`);
  }
});

// === Copy All Button ===
copyAllBtn.addEventListener('click', () => {
  if (uploadedFiles.length === 0) {
    alert('No documents to copy!');
    return;
  }
  
  // Create tab-separated rows: Filename\tID\tTimestamp (one per line)
  const tsvData = uploadedFiles
    .filter(file => file.id && file.id !== 'unknown')
    .map(file => {
      const date = file.timestamp ? new Date(file.timestamp).toLocaleString() : 'N/A';
      return `${file.name}\t${file.id}\t${date}`;
    })
    .join('\n');
  
  if (tsvData) {
    navigator.clipboard.writeText(tsvData);
    alert(`📋 Copied ${uploadedFiles.length} document(s)! (Filename, ID, date)\nPaste into Google Sheets - each part will go into a separate column.`);
  } else {
    alert('No valid documents to copy!');
  }
});

// === Archive Modal ===
viewArchiveBtn.addEventListener('click', () => {
  archiveModal.classList.remove('hidden');
  renderArchive();
});

if (closeArchiveBtn) {
  closeArchiveBtn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('Close button clicked');
    archiveModal.classList.add('hidden');
  });
}

// Close modal when clicking outside the content
if (archiveModal) {
  archiveModal.addEventListener('click', (e) => {
    if (e.target === archiveModal) {
      console.log('Outside clicked');
      archiveModal.classList.add('hidden');
    }
  });
}

function renderArchive() {
  archiveList.innerHTML = '';
  const archive = cleanExpiredArchive();

  if (archive.length === 0) {
    archiveList.innerHTML = '<li>No archived files.</li>';
    return;
  }

  archive.forEach(file => {
    const li = document.createElement('li');
    li.innerHTML = `
      <span title="${file.name}">${file.name}</span>
      <button data-id="${file.id}" data-name="${file.name}">Restore</button>
    `;
    archiveList.appendChild(li);
  });

  archiveList.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.dataset.id;
      const name = btn.dataset.name;

      const archive = cleanExpiredArchive().filter(f => f.id !== id);
      saveArchive(archive);

      uploadedFiles.push({ name, id });
      saveUploadedFiles(uploadedFiles);
      renderArchive();
      updateDropdown();
    });
  });
}