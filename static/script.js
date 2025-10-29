console.log('✅ SCRIPT FILE LOADED - TOP OF FILE');

// Run immediately if DOM is ready, otherwise wait for DOMContentLoaded
(function() {
console.log('✅ IIFE STARTED, readyState:', document.readyState);
if (document.readyState === 'loading') {
  console.log('⏳ Waiting for DOMContentLoaded...');
  document.addEventListener('DOMContentLoaded', init);
} else {
  console.log('✅ DOM already ready, calling init()');
  init();
}

function init() {
console.log('✅ INIT FUNCTION CALLED');
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

// === Error Modal ===
const errorModal = document.getElementById('error-modal');
const errorModalMessage = document.getElementById('error-modal-message');
const errorModalOk = document.getElementById('error-modal-ok');

function showError(message) {
  if (errorModalMessage && errorModal) {
    errorModalMessage.textContent = message;
    errorModal.classList.remove('hidden');
  } else {
    console.error('Error modal not found:', message);
  }
}

function hideError() {
  if (errorModal) {
    errorModal.classList.add('hidden');
  }
}

if (errorModalOk) {
  errorModalOk.addEventListener('click', hideError);
}

// Close modal when clicking outside
if (errorModal) {
  errorModal.addEventListener('click', (e) => {
    if (e.target === errorModal) {
      hideError();
    }
  });
}

// === Notification Sound ===
// Initialize AudioContext on first user interaction (for iOS compatibility)
let audioContext = null;

function initAudioContext() {
  if (!audioContext) {
    try {
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      // Resume context in case it's suspended (iOS requirement)
      if (audioContext.state === 'suspended') {
        audioContext.resume();
      }
      console.log('✅ AudioContext initialized for notifications');
    } catch (error) {
      console.log('AudioContext not available:', error);
    }
  }
  return audioContext;
}

function playNotificationSound() {
  try {
    const ctx = audioContext || initAudioContext();
    if (!ctx) return;
    
    // Resume if suspended (iOS often suspends audio contexts)
    if (ctx.state === 'suspended') {
      ctx.resume().then(() => {
        playSound(ctx);
      });
    } else {
      playSound(ctx);
    }
  } catch (error) {
    console.log('Notification sound error:', error);
  }
}

function playSound(ctx) {
  const oscillator = ctx.createOscillator();
  const gainNode = ctx.createGain();
  
  oscillator.connect(gainNode);
  gainNode.connect(ctx.destination);
  
  // Delicate "ting" like iPhone - high pitch, very short
  oscillator.frequency.value = 1200;
  oscillator.type = 'sine';
  
  // Very quick fade out for dainty sound
  gainNode.gain.setValueAtTime(0.15, ctx.currentTime);
  gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.2);
  
  oscillator.start(ctx.currentTime);
  oscillator.stop(ctx.currentTime + 0.2);
}

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

let currentDocumentId = null;

// === Persistent Storage ===
const STORAGE_KEY = 'axis_mind_uploads';

function loadUploadedFiles() {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored ? JSON.parse(stored) : [];
}

function saveUploadedFiles(files) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(files));
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
let uploadSoundPlayed = false; // Track if completion sound was played for this batch
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
  // Initialize audio context for notification (iOS compatibility)
  initAudioContext();
  
  const pdfFiles = files.filter(f => f.type === 'application/pdf');
  
  if (pdfFiles.length === 0) {
    status.textContent = '❌ Please upload valid PDF file(s).';
    return;
  }

  // Reset stats and show upload section
  uploadStats = { uploaded: pdfFiles.length, completed: 0, errors: 0 };
  activeUploads = []; // Clear previous uploads
  uploadsCancelled = false; // Reset cancellation flag
  uploadSoundPlayed = false; // Reset sound flag for new batch
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
  // Check file size and warn for very large files
  const fileSizeMB = file.size / (1024 * 1024);
  if (fileSizeMB > 20) {
    const proceed = confirm(`⚠️ This file is ${fileSizeMB.toFixed(1)}MB. Large files may take several minutes to process. Continue?`);
    if (!proceed) {
      uploadStats.errors++;
      updateStats();
      return;
    }
  }

  uploadItem.innerHTML = `
    <div class="upload-filename">${file.name}${fileSizeMB > 10 ? ` (${fileSizeMB.toFixed(1)}MB)` : ''}</div>
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

  // Simulate progress while reading file (slower for large files)
  let progress = 0;
  const progressSpeed = fileSizeMB > 10 ? 200 : 100;
  const progressInterval = setInterval(() => {
    progress += 10;
    if (progress <= 50) {
      progressBar.style.width = `${progress}%`;
    }
  }, progressSpeed);

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

  // Upload directly without base64 conversion (more efficient!)
  (async () => {
    try {
      await new Promise(resolve => setTimeout(resolve, 500)); // Small delay for UX
      clearInterval(progressInterval);
      progressBar.style.width = '60%';

      console.log('📤 Starting upload for:', file.name, 'Size:', (file.size / 1024 / 1024).toFixed(2), 'MB');

      // Use FormData for efficient binary upload (no base64 bloat!)
      const formData = new FormData();
      formData.append('file', file);

      console.log('📡 Sending fetch request to /upload');

      // Extended timeout for OCR processing (15 minutes)
      const timeoutId = setTimeout(() => abortController.abort(), 15 * 60 * 1000);
      
      const res = await fetch('/upload', {
        method: 'POST',
        body: formData,
        signal: abortController.signal
      });
      
      clearTimeout(timeoutId);

      console.log('✅ Got response:', res.status, res.statusText);

      progressBar.style.width = '80%';

      const result = await res.json();
      console.log('📦 Response data:', result);

      if (!res.ok) {
        throw new Error(result.error || `Upload failed with status ${res.status}`);
      }

      // Success
      currentDocumentId = result.document_id;

      uploadedFiles = uploadedFiles.filter(f => f.name !== file.name);
      uploadedFiles.push({ 
        name: file.name, 
        id: result.document_id,
        timestamp: Date.now()
      });
      saveUploadedFiles(uploadedFiles);
      
      // Save tags if present (InnerVerse Intelligence Layer)
      if (result.tags && Array.isArray(result.tags) && result.tags.length > 0) {
        saveDocumentTags(result.document_id, file.name, result.tags);
        console.log(`🏷️ Document tagged with ${result.tags.length} concepts:`, result.tags.slice(0, 5));
      } else {
        // Warn user that auto-tagging failed (but upload succeeded)
        console.warn('⚠️ Auto-tagging failed for:', file.name);
        showError(`⚠️ "${file.name}" uploaded successfully, but auto-tagging failed. Your document is fully searchable, but won't appear in the tag library.`);
      }

      progressBar.style.width = '100%';
      uploadItem.classList.add('success');
      uploadStats.completed++;
      updateStats();

      // Copy first successful document ID
      if (uploadStats.completed === 1) {
        navigator.clipboard.writeText(result.document_id);
      }
    } catch (err) {
      clearInterval(progressInterval);
      console.error('❌ Upload error:', err);
      if (err.name === 'AbortError') {
        // Upload was cancelled
        uploadItem.classList.add('error');
        uploadItem.querySelector('.upload-filename').textContent = `${file.name} (Cancelled)`;
      } else {
        progressBar.style.width = '100%';
        uploadItem.classList.add('error');
        
        // Better error message extraction
        let errorMsg = 'Upload failed';
        if (err.message) {
          errorMsg = err.message;
        } else if (typeof err === 'string') {
          errorMsg = err;
        } else if (err.toString && err.toString() !== '[object Object]') {
          errorMsg = err.toString();
        }
        
        uploadItem.querySelector('.upload-filename').textContent = `${file.name} - ${errorMsg}`;
        uploadStats.errors++;
        updateStats();
        
        // Show persistent error modal
        showError(`Upload failed for "${file.name}": ${errorMsg}`);
      }
    } finally {
      // Remove from active uploads
      activeUploads = activeUploads.filter(u => u.itemId !== itemId);
      checkUploadComplete();
    }
  })();
}

// Check if all uploads are complete and hide cancel button
function checkUploadComplete() {
  if (activeUploads.length === 0) {
    cancelUploadBtn.classList.add('hidden');
    
    // Play notification sound if any uploads succeeded (only once per batch)
    if (uploadStats.completed > 0 && !uploadSoundPlayed) {
      playNotificationSound();
      uploadSoundPlayed = true; // Mark as played for this batch
    }
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
    // Check if on mobile device
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    if (isMobile) {
      showError('📱 Google Drive integration is only available on desktop. Please use a computer to upload from Google Drive, or use the "Start uploading" button to upload files directly from your mobile device.');
      return;
    }
    
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
      showError('Google Drive not properly configured. Please contact support.');
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
    showError('Failed to open Google Drive picker: ' + error.message);
  }
});

// Handle picker selection
async function pickerCallback(data) {
  if (data.action === google.picker.Action.PICKED) {
    const files = data.docs.filter(doc => doc.mimeType === 'application/pdf');
    
    if (files.length === 0) {
      showError('Please select PDF files only.');
      return;
    }

    // Setup upload tracking
    uploadStats = { uploaded: files.length, completed: 0, errors: 0 };
    activeUploads = [];
    uploadsCancelled = false;
    uploadSoundPlayed = false; // Reset sound flag for new batch
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
      
      // Save tags if present (InnerVerse Intelligence Layer)
      if (result.tags && Array.isArray(result.tags)) {
        saveDocumentTags(result.document_id, fileName, result.tags);
        console.log(`🏷️ Document tagged with ${result.tags.length} concepts:`, result.tags.slice(0, 5));
      }
      
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
      
      // Show persistent error modal
      let errorMsg = error.message || 'Upload failed';
      showError(`Google Drive upload failed for "${fileName}": ${errorMsg}`);
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

  appendMessage('user', question);
  sendBtn.disabled = true;

  // Check if this is a command
  const isCommand = await handleChatCommand(question);
  
  if (!isCommand) {
    // Not a command, search ALL documents by sending empty document_id
    const documentIdToUse = "";  // Empty = search all docs
    appendMessage('bot', '🧠 Searching all documents...');

    try {
      const res = await fetch('/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: documentIdToUse, question })
      });

      const data = await res.json();
      removeLastBotMessage();

      if (res.ok) {
        appendMessage('bot', data.answer || 'No response.');
      } else {
        removeLastBotMessage();
        showError('Chat query failed: ' + (data.error || 'Unknown error'));
      }
    } catch (err) {
      removeLastBotMessage();
      showError('Chat error: ' + err.message);
    }
  }

  sendBtn.disabled = false;
  chatInput.value = '';
}

// Handle chat commands
async function handleChatCommand(input) {
  const lowerInput = input.toLowerCase().trim();
  
  // Help command
  if (lowerInput === 'help' || lowerInput === '/help') {
    appendMessage('bot', `📋 Available Commands:

• list docs - Show all uploaded documents

• show doc [id] - Display document details

• delete doc [id] - Delete a specific document

• help - Show this help message

💬 Or just ask any question to search all your documents!`);
    return true;
  }
  
  // List docs command
  if (lowerInput === 'list docs' || lowerInput === 'list' || lowerInput === 'show docs') {
    appendMessage('bot', '📂 Loading your documents...');
    
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      const docs = stored ? JSON.parse(stored) : [];
      
      removeLastBotMessage();
      
      if (docs.length === 0) {
        appendMessage('bot', '📭 No documents uploaded yet. Upload a PDF to get started!');
      } else {
        let message = `📚 Your Documents (${docs.length}):\n\n`;
        docs.forEach((doc, index) => {
          const date = new Date(doc.timestamp).toLocaleString();
          message += `${index + 1}. ${doc.name}\n   ID: ${doc.id}\n   Uploaded: ${date}\n\n`;
        });
        appendMessage('bot', message);
      }
    } catch (error) {
      removeLastBotMessage();
      showError('Failed to load documents: ' + error.message);
    }
    
    return true;
  }
  
  // Show doc command
  const showDocMatch = lowerInput.match(/^show doc (.+)$/);
  if (showDocMatch) {
    const docId = showDocMatch[1].trim();
    appendMessage('bot', `🔍 Looking up document: ${docId}...`);
    
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      const docs = stored ? JSON.parse(stored) : [];
      const doc = docs.find(d => d.id === docId);
      
      removeLastBotMessage();
      
      if (doc) {
        const date = new Date(doc.timestamp).toLocaleString();
        appendMessage('bot', `📄 Document Details:
        
Name: ${doc.name}
ID: ${doc.id}
Uploaded: ${date}`);
      } else {
        appendMessage('bot', `❌ Document not found: ${docId}\n\nType "list docs" to see all available documents.`);
      }
    } catch (error) {
      removeLastBotMessage();
      showError('Failed to show document: ' + error.message);
    }
    
    return true;
  }
  
  // Delete doc command
  const deleteDocMatch = lowerInput.match(/^delete doc (.+)$/);
  if (deleteDocMatch) {
    const docId = deleteDocMatch[1].trim();
    
    if (!confirm(`⚠️ Delete document "${docId}"?\n\nThis will remove all data from Pinecone. This cannot be undone!`)) {
      appendMessage('bot', '❌ Delete cancelled.');
      return true;
    }
    
    appendMessage('bot', `🗑️ Deleting document: ${docId}...`);
    
    try {
      const response = await fetch(`/documents/${docId}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        throw new Error('Failed to delete document');
      }
      
      // Remove from localStorage
      const stored = localStorage.getItem(STORAGE_KEY);
      const docs = stored ? JSON.parse(stored) : [];
      const updatedDocs = docs.filter(d => d.id !== docId);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedDocs));
      uploadedFiles = updatedDocs;
      
      removeLastBotMessage();
      appendMessage('bot', `✅ Document deleted successfully!\n\nDeleted: ${docId}`);
    } catch (error) {
      removeLastBotMessage();
      showError('Failed to delete document: ' + error.message);
    }
    
    return true;
  }
  
  return false; // Not a command
}

function appendMessage(sender, text) {
  const messageContainer = document.createElement('div');
  messageContainer.classList.add('message', sender);
  
  const bubble = document.createElement('div');
  bubble.classList.add('message-bubble');
  bubble.textContent = text;
  
  messageContainer.appendChild(bubble);
  chatLog.appendChild(messageContainer);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function removeLastBotMessage() {
  const messages = chatLog.querySelectorAll('.message.bot');
  if (messages.length > 0) messages[messages.length - 1].remove();
}

// === Delete All Documents (Temporary) ===
const deleteAllBtn = document.getElementById('delete-all-btn');

deleteAllBtn.addEventListener('click', async () => {
  if (!confirm('⚠️ Are you sure you want to delete ALL uploaded documents? This cannot be undone!')) {
    return;
  }
  
  try {
    deleteAllBtn.disabled = true;
    deleteAllBtn.textContent = '⏳ Deleting...';
    
    const response = await fetch('/documents/all', {
      method: 'DELETE'
    });
    
    // Also clear tagged documents from localStorage
    clearTaggedDocuments();
    
    if (!response.ok) {
      throw new Error('Failed to delete documents');
    }
    
    const data = await response.json();
    alert('✅ All documents deleted successfully!');
    
    // Clear localStorage
    localStorage.removeItem('uploadedDocuments');
    
    // Reload page to reset UI
    window.location.reload();
    
  } catch (error) {
    console.error('Delete all error:', error);
    showError('Error deleting documents: ' + error.message);
    deleteAllBtn.textContent = '🗑️ Delete All Files';
    deleteAllBtn.disabled = false;
  }
});

// === Download Document Report ===
const downloadReportBtn = document.getElementById('download-report-btn');

downloadReportBtn.addEventListener('click', async () => {
  try {
    downloadReportBtn.disabled = true;
    downloadReportBtn.textContent = '⏳ Generating report...';
    
    const response = await fetch('/documents/report');
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to generate report');
    }
    
    // Download the CSV file
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'document_report.csv';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    downloadReportBtn.textContent = '✅ Downloaded!';
    setTimeout(() => {
      downloadReportBtn.textContent = '📄 Download Document Report';
      downloadReportBtn.disabled = false;
    }, 2000);
  } catch (error) {
    console.error('Report download error:', error);
    showError('Failed to download report: ' + error.message);
    downloadReportBtn.textContent = '📄 Download Document Report';
    downloadReportBtn.disabled = false;
  }
});

// === YouTube Transcription ===
const youtubeUrl = document.getElementById('youtube-url');
const transcribeBtn = document.getElementById('transcribe-btn');
const youtubeStatus = document.getElementById('youtube-status');

let youtubeProgressInterval = null;
let youtubeAbortController = null;

if (transcribeBtn && youtubeUrl && youtubeStatus) {
  transcribeBtn.addEventListener('click', async () => {
    // Initialize audio context for notification (iOS compatibility)
    initAudioContext();
    
    const url = youtubeUrl.value.trim();
    
    if (!url) {
      showYoutubeStatus('Please enter a YouTube URL', 'error');
      return;
    }
    
    // Validate YouTube URL
    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/)/;
    if (!youtubeRegex.test(url)) {
      showYoutubeStatus('Please enter a valid YouTube URL', 'error');
      return;
    }
    
    try {
      transcribeBtn.disabled = true;
      transcribeBtn.textContent = '⏳ Processing...';
      
      // Create abort controller
      youtubeAbortController = new AbortController();
      
      // Show progress bar
      showYoutubeProgress(0, 'Downloading audio...');
      
      // Simulate progress stages
      let progress = 0;
      youtubeProgressInterval = setInterval(() => {
        if (progress < 20) progress += 1; // Slow start for download
        else if (progress < 60) progress += 2; // Faster for transcription
        else if (progress < 90) progress += 1; // Slow down near end
        updateYoutubeProgress(progress);
      }, 300);
      
      // Add 60 minute timeout for very long videos (1+ hours)
      let isTimeout = false;
      const timeoutId = setTimeout(() => {
        isTimeout = true;
        youtubeAbortController.abort();
      }, 3600000); // 60 minutes
      
      const response = await fetch('/transcribe-youtube', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ youtube_url: url }),
        signal: youtubeAbortController.signal
      });
      
      clearTimeout(timeoutId);
      
      // Clear progress interval
      clearInterval(youtubeProgressInterval);
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Transcription failed');
      }
      
      // Show completion
      updateYoutubeProgress(100, 'Complete!');
      
      // Download the PDF
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      
      // Extract filename from Content-Disposition header or use default
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = 'youtube_transcript.pdf';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(downloadUrl);
      document.body.removeChild(a);
      
      setTimeout(() => {
        hideYoutubeProgress();
        showYoutubeStatus('✅ PDF downloaded! You can now upload it to InnerVerse.', 'success');
        playNotificationSound(); // Play notification ping
      }, 500);
      
      youtubeUrl.value = '';
      transcribeBtn.textContent = 'Transcribe';
      transcribeBtn.disabled = false;
      
    } catch (error) {
      clearInterval(youtubeProgressInterval);
      hideYoutubeProgress();
      
      if (error.name === 'AbortError') {
        if (isTimeout) {
          showError('Transcription timeout: This video is taking too long to process (over 60 minutes). The video may be extremely long, have network issues, or YouTube restrictions. Try a shorter video or check your connection.');
        } else {
          showYoutubeStatus('⚠️ Transcription cancelled', 'error');
        }
      } else {
        console.error('YouTube transcription error:', error);
        showError('YouTube transcription failed: ' + error.message);
      }
      
      transcribeBtn.textContent = 'Transcribe';
      transcribeBtn.disabled = false;
    }
  });
}

// Enter key support for YouTube input
if (youtubeUrl && transcribeBtn) {
  youtubeUrl.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !transcribeBtn.disabled) {
      transcribeBtn.click();
    }
  });
}

if (!transcribeBtn || !youtubeUrl || !youtubeStatus) {
  console.error('❌ YouTube transcription elements not found in DOM');
}

function showYoutubeStatus(message, type) {
  youtubeStatus.innerHTML = message;
  youtubeStatus.className = 'youtube-status ' + type;
  youtubeStatus.classList.remove('hidden');
  
  if (type === 'error') {
    setTimeout(() => {
      youtubeStatus.classList.add('hidden');
    }, 15000);
  }
}

function showYoutubeProgress(percent, statusText) {
  const youtubeSection = document.querySelector('.youtube-section');
  
  // Remove existing cancel button if present
  const existingCancel = youtubeSection.querySelector('.youtube-cancel-btn');
  if (existingCancel) {
    existingCancel.remove();
  }
  
  // Add cancel button to YouTube section (top right corner)
  const cancelBtn = document.createElement('button');
  cancelBtn.className = 'youtube-cancel-btn';
  cancelBtn.innerHTML = '✕ Cancel';
  cancelBtn.onclick = cancelYoutubeTranscription;
  youtubeSection.appendChild(cancelBtn);
  
  // Show progress bar without cancel button inside
  youtubeStatus.innerHTML = `
    <div class="youtube-progress-container">
      <div class="youtube-progress-bar">
        <div class="youtube-progress-fill" style="width: ${percent}%"></div>
        <span class="youtube-progress-text">${percent}% - ${statusText}</span>
      </div>
    </div>
  `;
  youtubeStatus.className = 'youtube-status processing';
  youtubeStatus.classList.remove('hidden');
}

function updateYoutubeProgress(percent, statusText = 'Processing...') {
  const fill = youtubeStatus.querySelector('.youtube-progress-fill');
  const text = youtubeStatus.querySelector('.youtube-progress-text');
  
  if (fill && text) {
    fill.style.width = percent + '%';
    text.textContent = `${percent}% - ${statusText}`;
  }
}

function hideYoutubeProgress() {
  youtubeStatus.classList.add('hidden');
  
  // Remove cancel button when hiding progress
  const youtubeSection = document.querySelector('.youtube-section');
  const cancelBtn = youtubeSection.querySelector('.youtube-cancel-btn');
  if (cancelBtn) {
    cancelBtn.remove();
  }
}

function cancelYoutubeTranscription() {
  if (youtubeAbortController) {
    youtubeAbortController.abort();
    clearInterval(youtubeProgressInterval);
    
    // Remove cancel button
    const youtubeSection = document.querySelector('.youtube-section');
    const cancelBtn = youtubeSection.querySelector('.youtube-cancel-btn');
    if (cancelBtn) {
      cancelBtn.remove();
    }
  }
}

// === Text to PDF Collapsible Toggle ===
const textPdfToggle = document.getElementById('text-pdf-toggle');
const textPdfContent = document.getElementById('text-pdf-content');

// Start collapsed by default
textPdfToggle.classList.add('collapsed');
textPdfContent.classList.add('collapsed');

textPdfToggle.addEventListener('click', () => {
  textPdfToggle.classList.toggle('collapsed');
  textPdfContent.classList.toggle('collapsed');
});

// === Cost Tracker Collapsible Toggle ===
const costTrackerToggle = document.getElementById('cost-tracker-toggle');
const costTrackerContent = document.getElementById('cost-tracker-content');

// Start COLLAPSED by default
if (costTrackerToggle && costTrackerContent) {
  costTrackerToggle.classList.add('collapsed');
  costTrackerContent.classList.add('collapsed');
  
  costTrackerToggle.addEventListener('click', () => {
    costTrackerToggle.classList.toggle('collapsed');
    costTrackerContent.classList.toggle('collapsed');
  });
}

// === Text to PDF Feature ===
const pdfTitle = document.getElementById('pdf-title');
const pdfText = document.getElementById('pdf-text');
const createPdfBtn = document.getElementById('create-pdf-btn');
const textPdfProgress = document.getElementById('text-pdf-progress');

createPdfBtn.addEventListener('click', async () => {
  // Initialize audio context for notification (iOS compatibility)
  initAudioContext();
  
  const title = pdfTitle.value.trim() || 'Document';
  const text = pdfText.value.trim();
  
  if (!text) {
    showTextPdfError('Please enter some text to convert to PDF');
    return;
  }
  
  if (text.length < 10) {
    showTextPdfError('Text is too short. Please add more content.');
    return;
  }
  
  try {
    createPdfBtn.disabled = true;
    createPdfBtn.textContent = '⏳ Processing...';
    
    // Show progress bar
    textPdfProgress.classList.remove('hidden');
    updateTextPdfProgress('✨ Analyzing text...', 20);
    
    // Small delay for visual feedback
    await new Promise(resolve => setTimeout(resolve, 300));
    updateTextPdfProgress('🔧 Fixing punctuation and grammar...', 50);
    
    const response = await fetch('/text-to-pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        text: text,
        title: title 
      })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'PDF creation failed');
    }
    
    updateTextPdfProgress('📄 Generating PDF...', 80);
    
    // Download the PDF
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    
    // Extract filename from Content-Disposition header or use default
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = 'document.pdf';
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
      if (filenameMatch) {
        filename = filenameMatch[1];
      }
    }
    
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(downloadUrl);
    document.body.removeChild(a);
    
    updateTextPdfProgress('✅ PDF created successfully!', 100);
    playNotificationSound(); // Play notification ping
    
    // Clear inputs after success
    setTimeout(() => {
      pdfTitle.value = '';
      pdfText.value = '';
      textPdfProgress.classList.add('hidden');
    }, 3000);
    
  } catch (error) {
    console.error('Text to PDF error:', error);
    textPdfProgress.classList.add('hidden');
    showError('Text to PDF failed: ' + error.message);
  } finally {
    createPdfBtn.disabled = false;
    createPdfBtn.textContent = '✨ Create PDF';
  }
});

function updateTextPdfProgress(message, percentage) {
  const statusText = textPdfProgress.querySelector('.text-pdf-status-text');
  const progressBar = textPdfProgress.querySelector('.text-pdf-progress-bar');
  
  statusText.textContent = message;
  progressBar.style.width = percentage + '%';
}

function showTextPdfError(message) {
  textPdfProgress.classList.add('hidden');
  
  const errorDiv = document.createElement('div');
  errorDiv.className = 'text-pdf-status error';
  errorDiv.textContent = message;
  
  const form = document.querySelector('.text-pdf-form');
  const existingError = form.nextElementSibling;
  if (existingError && existingError.classList.contains('text-pdf-status')) {
    existingError.remove();
  }
  
  form.after(errorDiv);
  
  setTimeout(() => {
    errorDiv.remove();
  }, 5000);
}

// === Cost Tracker ===
async function updateCostTracker() {
  console.log('💰 updateCostTracker called!');
  try {
    const response = await fetch('/api/usage');
    if (!response.ok) {
      console.error('Failed to fetch usage data');
      return;
    }
    
    const data = await response.json();
    console.log('📊 Cost data received:', data);
    
    // Update total cost
    const totalCostEl = document.getElementById('total-cost');
    if (totalCostEl) {
      totalCostEl.textContent = `$${(data.total_cost || 0).toFixed(4)}`;
    }
    
    // Update 24h cost
    const cost24hEl = document.getElementById('cost-24h');
    if (cost24hEl) {
      cost24hEl.textContent = `$${(data.last_24h_cost || 0).toFixed(4)}`;
    }
    
    // Update breakdown by operation
    const breakdown = data.by_operation || {};
    const breakdownHtml = `
      <div class="cost-breakdown-item">
        <span>Claude: <strong>$${(breakdown.claude_chat?.cost || 0).toFixed(4)}</strong></span>
      </div>
      <div class="cost-breakdown-item">
        <span>GPT Chat: <strong>$${(breakdown.chat_completion?.cost || 0).toFixed(4)}</strong></span>
      </div>
      <div class="cost-breakdown-item">
        <span>Embeddings: <strong>$${(breakdown.query_embedding?.cost || 0).toFixed(4)}</strong></span>
      </div>
      <div class="cost-breakdown-item">
        <span>Auto-Tagging: <strong>$${(breakdown.auto_tagging?.cost || 0).toFixed(4)}</strong></span>
      </div>
      <div class="cost-breakdown-item">
        <span>Whisper: <strong>$${(breakdown.whisper?.cost || 0).toFixed(4)}</strong></span>
      </div>
      <div class="cost-breakdown-item">
        <span>Text Fix: <strong>$${(breakdown.text_fix?.cost || 0).toFixed(4)}</strong></span>
      </div>
    `;
    const costByOpEl = document.getElementById('cost-by-operation');
    if (costByOpEl) {
      costByOpEl.innerHTML = breakdownHtml;
    }
    
    // Update recent calls
    const recentCallsDiv = document.getElementById('recent-calls');
    if (recentCallsDiv) {
      if (data.recent_calls && data.recent_calls.length > 0) {
        const recentHtml = data.recent_calls.slice(0, 10).map(call => `
          <div class="recent-call-item">
            <span class="recent-call-operation">${formatOperation(call.operation)}</span>
            <span class="recent-call-cost">$${call.cost.toFixed(4)}</span>
          </div>
        `).join('');
        recentCallsDiv.innerHTML = recentHtml;
      } else {
        recentCallsDiv.innerHTML = '<div class="recent-call-placeholder">No recent activity</div>';
      }
    }
    
  } catch (error) {
    console.error('Error updating cost tracker:', error);
  }
}

function formatOperation(operation) {
  const formats = {
    'claude_chat': '🤖 Claude',
    'chat_completion': '💬 GPT Chat',
    'query_embedding': '📊 Embedding',
    'embedding': '📊 Embedding',
    'auto_tagging': '🏷️ Auto-Tag',
    'whisper': '🎤 Whisper',
    'text_fix': '✨ Text Fix'
  };
  return formats[operation] || operation;
}

// Update cost tracker on page load and every 30 seconds
console.log('🚀 Script loaded, calling updateCostTracker...');
updateCostTracker();
setInterval(updateCostTracker, 30000);

} // end init function
})(); // end IIFE

// === YouTube Collapsible Toggle ===
const youtubeToggle = document.getElementById('youtube-toggle');
const youtubeContent = document.getElementById('youtube-content');

// Start collapsed by default (closed)
if (youtubeToggle && youtubeContent) {
  youtubeToggle.classList.add('collapsed');
  youtubeContent.classList.add('collapsed');
  
  youtubeToggle.addEventListener('click', () => {
    youtubeToggle.classList.toggle('collapsed');
    youtubeContent.classList.toggle('collapsed');
  });
}

// === Text to PDF - Start OPEN by default ===
const textPdfToggle = document.getElementById('text-pdf-toggle');
const textPdfContent = document.getElementById('text-pdf-content');

if (textPdfToggle && textPdfContent) {
  // Remove collapsed class to start open
  textPdfToggle.classList.remove('collapsed');
  textPdfContent.classList.remove('collapsed');
  
  textPdfToggle.addEventListener('click', () => {
    textPdfToggle.classList.toggle('collapsed');
    textPdfContent.classList.toggle('collapsed');
  });
}

// === Tag Library Collapsible Toggle ===
const tagLibraryToggle = document.getElementById('tag-library-toggle');
const tagLibraryContent = document.getElementById('tag-library-content');

// Start collapsed by default
if (tagLibraryToggle && tagLibraryContent) {
  tagLibraryToggle.classList.add('collapsed');
  tagLibraryContent.classList.add('collapsed');
  
  tagLibraryToggle.addEventListener('click', () => {
    tagLibraryToggle.classList.toggle('collapsed');
    tagLibraryToggle.classList.toggle('open');
    tagLibraryContent.classList.toggle('collapsed');
    tagLibraryContent.classList.toggle('open');
    
    // Load tag library when opened
    if (tagLibraryContent.classList.contains('open')) {
      loadTagLibrary();
    }
  });
}

// === Tag Library Functions ===
function saveDocumentTags(documentId, filename, tags) {
  const taggedDocs = JSON.parse(localStorage.getItem('innerverse_tagged_docs') || '{}');
  taggedDocs[documentId] = {
    filename: filename,
    tags: tags || [],
    timestamp: Date.now()
  };
  localStorage.setItem('innerverse_tagged_docs', JSON.stringify(taggedDocs));
  console.log(`💾 Saved ${tags?.length || 0} tags for document: ${filename}`);
}

function getTaggedDocuments() {
  return JSON.parse(localStorage.getItem('innerverse_tagged_docs') || '{}');
}

function clearTaggedDocuments() {
  localStorage.removeItem('innerverse_tagged_docs');
  console.log('🗑️ Cleared all tagged documents from localStorage');
}

async function loadTagLibrary() {
  try {
    // Fetch from backend API (Pinecone) instead of localStorage
    const response = await fetch('/api/tagged-documents');
    const data = await response.json();
    
    if (!data.documents || Object.keys(data.documents).length === 0) {
      document.getElementById('tag-cloud').innerHTML = '<div class="tag-cloud-placeholder">Upload documents to see extracted tags...</div>';
      document.getElementById('tagged-documents-list').innerHTML = '<div class="tagged-documents-placeholder">No tagged documents yet. Upload a PDF to see auto-extracted MBTI tags!</div>';
      return;
    }
    
    const taggedDocs = data.documents;
    const docCount = Object.keys(taggedDocs).length;
    
    console.log(`📚 Loading tag library with ${docCount} documents from Pinecone`);
    
    // Build tag frequency map
    const tagFrequency = {};
    Object.values(taggedDocs).forEach(doc => {
      if (doc.tags && Array.isArray(doc.tags)) {
        doc.tags.forEach(tag => {
          tagFrequency[tag] = (tagFrequency[tag] || 0) + 1;
        });
      }
    });
    
    // Sort tags by frequency
    const sortedTags = Object.entries(tagFrequency)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 30); // Top 30 tags
    
    // Build tag cloud
    const tagCloudHTML = sortedTags.map(([tag, count]) => 
      `<div class="tag-badge clickable" onclick="filterByTag('${tag}')">
        ${tag}
        <span class="tag-count">${count}</span>
      </div>`
    ).join('');
    
    document.getElementById('tag-cloud').innerHTML = tagCloudHTML || '<div class="tag-cloud-placeholder">No tags extracted yet</div>';
    
    // Build document list
    const docsArray = Object.entries(taggedDocs)
      .map(([id, doc]) => ({ id, ...doc }))
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    const docsHTML = docsArray.map(doc => `
      <div class="tagged-document-item">
        <div class="tagged-document-title">${doc.filename}</div>
        <div class="tagged-document-tags">
          ${doc.tags && doc.tags.length > 0 
            ? doc.tags.map(tag => `<span class="tag-mini">${tag}</span>`).join('')
            : '<span class="tag-mini" style="opacity: 0.5;">No tags</span>'
          }
        </div>
        <div class="tagged-document-meta">
          <span>🏷️ ${doc.tags?.length || 0} tags</span>
          <span>📅 ${new Date(doc.timestamp).toLocaleDateString()}</span>
        </div>
      </div>
    `).join('');
    
    document.getElementById('tagged-documents-list').innerHTML = docsHTML;
    console.log(`✅ Tag library loaded: ${sortedTags.length} tags, ${docsArray.length} documents`);
  } catch (error) {
    console.error('❌ Error loading tag library:', error);
    document.getElementById('tag-cloud').innerHTML = '<div class="tag-cloud-placeholder">Error loading tags...</div>';
  }
}

function filterByTag(tag) {
  console.log(`🔍 Filtering by tag: ${tag}`);
  // TODO: Could implement filtering in the document list
  // For now, just highlight the tag
  alert(`Filter by tag: ${tag}\n\nThis will search documents tagged with "${tag}"`);
}
