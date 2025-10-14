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

let uploadStats = { uploaded: 0, completed: 0, errors: 0 };

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
  updateStats();
  uploadStatusSection.classList.remove('hidden');
  uploadList.innerHTML = '';
  status.textContent = '';

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
        body: JSON.stringify(payload)
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
      progressBar.style.width = '100%';
      uploadItem.classList.add('error');
      uploadStats.errors++;
      updateStats();
    }
  };

  reader.readAsDataURL(file);
}

// === Google Drive Integration ===
let pickerApiLoaded = false;
let accessToken = null;

function loadPickerApi() {
  gapi.load('picker', () => {
    pickerApiLoaded = true;
  });
}

async function openGoogleDrivePicker() {
  try {
    // Get access token from backend
    const tokenResponse = await fetch('/api/gdrive-token');
    const tokenData = await tokenResponse.json();
    
    if (!tokenData.access_token) {
      alert('❌ Google Drive not connected. Please contact support.');
      return;
    }
    
    accessToken = tokenData.access_token;
    
    // Wait for picker API to load
    if (!pickerApiLoaded) {
      if (typeof gapi !== 'undefined') {
        loadPickerApi();
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    }
    
    // Create picker
    const picker = new google.picker.PickerBuilder()
      .addView(new google.picker.DocsView()
        .setIncludeFolders(true)
        .setMimeTypes('application/pdf'))
      .setOAuthToken(accessToken)
      .setCallback(pickerCallback)
      .setTitle('Select PDF files from Google Drive')
      .enableFeature(google.picker.Feature.MULTISELECT_ENABLED)
      .build();
    
    picker.setVisible(true);
  } catch (error) {
    console.error('Picker error:', error);
    alert('❌ Failed to open Google Drive picker: ' + error.message);
  }
}

async function pickerCallback(data) {
  if (data.action === google.picker.Action.PICKED) {
    const files = data.docs.filter(doc => doc.mimeType === 'application/pdf');
    
    if (files.length === 0) {
      alert('❌ Please select PDF files only.');
      return;
    }
    
    // Setup upload tracking
    uploadStats = { uploaded: files.length, completed: 0, errors: 0 };
    updateStats();
    uploadStatusSection.classList.remove('hidden');
    uploadList.innerHTML = '';
    status.textContent = '';
    
    // Download and process each file
    for (const file of files) {
      await downloadAndProcessGDriveFile(file.id, file.name);
    }
  }
}

async function downloadAndProcessGDriveFile(fileId, fileName) {
  // Create upload item for tracking
  const uploadItem = document.createElement('div');
  uploadItem.className = 'upload-item';
  uploadItem.innerHTML = `
    <div class="upload-filename">${fileName}</div>
    <div class="progress-bar-container">
      <div class="progress-bar"></div>
    </div>
  `;
  uploadList.appendChild(uploadItem);
  
  const progressBar = uploadItem.querySelector('.progress-bar');
  progressBar.style.width = '30%';
  
  try {
    // Download from Google Drive
    const response = await fetch(`/api/gdrive-download/${fileId}`);
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
      body: JSON.stringify(payload)
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
    console.error('GDrive file error:', error);
    progressBar.style.width = '100%';
    uploadItem.classList.add('error');
    uploadStats.errors++;
    updateStats();
  }
}

// Load picker API when gapi is ready
if (typeof gapi !== 'undefined') {
  gapi.load('picker', () => {
    pickerApiLoaded = true;
  });
}

// Attach event listener to Google Drive button
gdriveBtn.addEventListener('click', openGoogleDrivePicker);

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
  dropdownMenu.classList.toggle('hidden');
  updateDropdown();
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
      <div class="doc-info">
        <div class="doc-name" title="${file.name}">${file.name}</div>
        <div class="doc-meta">
          <span class="doc-id" title="${fullId}">ID: ${shortId}</span>
          <span class="doc-date">${date}</span>
        </div>
      </div>
      <div class="doc-actions">
        <button class="copy-btn" data-id="${fullId}">Copy</button>
        <button class="delete-btn" data-id="${fullId}">Delete</button>
      </div>
    `;
    docList.appendChild(li);
  });

  dropdownMenu.classList.remove('hidden');

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
      
      // Tab-separated format for Google Sheets: ID\tFilename\tTimestamp
      const tsvData = `${file.id}\t${file.name}\t${date}`;
      
      navigator.clipboard.writeText(tsvData);
      alert('📋 Document info copied! (ID, filename, date)');
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

// === Copy All Button ===
copyAllBtn.addEventListener('click', () => {
  if (uploadedFiles.length === 0) {
    alert('No documents to copy!');
    return;
  }
  
  // Create tab-separated rows: ID\tFilename\tTimestamp (one per line)
  const tsvData = uploadedFiles
    .filter(file => file.id && file.id !== 'unknown')
    .map(file => {
      const date = file.timestamp ? new Date(file.timestamp).toLocaleString() : 'N/A';
      return `${file.id}\t${file.name}\t${date}`;
    })
    .join('\n');
  
  if (tsvData) {
    navigator.clipboard.writeText(tsvData);
    alert(`📋 Copied ${uploadedFiles.length} document(s)! (ID, filename, date)\nPaste into Google Sheets - each part will go into a separate column.`);
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