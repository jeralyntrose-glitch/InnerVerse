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
    alert('❌ Error deleting documents: ' + error.message);
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
    alert('❌ Failed to download report: ' + error.message);
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

transcribeBtn.addEventListener('click', async () => {
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
    
    const response = await fetch('/transcribe-youtube', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ youtube_url: url }),
      signal: youtubeAbortController.signal
    });
    
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
      showYoutubeStatus('✅ PDF downloaded! You can now upload it to Axis Mind.', 'success');
    }, 500);
    
    youtubeUrl.value = '';
    transcribeBtn.textContent = 'Transcribe';
    transcribeBtn.disabled = false;
    
  } catch (error) {
    clearInterval(youtubeProgressInterval);
    hideYoutubeProgress();
    
    if (error.name === 'AbortError') {
      showYoutubeStatus('⚠️ Transcription cancelled', 'error');
    } else {
      console.error('YouTube transcription error:', error);
      showYoutubeStatus('❌ ' + error.message, 'error');
    }
    
    transcribeBtn.textContent = 'Transcribe';
    transcribeBtn.disabled = false;
  }
});

// Enter key support for YouTube input
youtubeUrl.addEventListener('keypress', (e) => {
  if (e.key === 'Enter' && !transcribeBtn.disabled) {
    transcribeBtn.click();
  }
});

function showYoutubeStatus(message, type) {
  youtubeStatus.innerHTML = message;
  youtubeStatus.className = 'youtube-status ' + type;
  youtubeStatus.classList.remove('hidden');
  
  if (type === 'error') {
    setTimeout(() => {
      youtubeStatus.classList.add('hidden');
    }, 5000);
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

// === Text to PDF Feature ===
const pdfTitle = document.getElementById('pdf-title');
const pdfText = document.getElementById('pdf-text');
const createPdfBtn = document.getElementById('create-pdf-btn');
const textPdfStatus = document.getElementById('text-pdf-status');

createPdfBtn.addEventListener('click', async () => {
  const title = pdfTitle.value.trim() || 'Document';
  const text = pdfText.value.trim();
  
  if (!text) {
    showTextPdfStatus('Please enter some text to convert to PDF', 'error');
    return;
  }
  
  if (text.length < 10) {
    showTextPdfStatus('Text is too short. Please add more content.', 'error');
    return;
  }
  
  try {
    createPdfBtn.disabled = true;
    createPdfBtn.textContent = '⏳ Processing...';
    showTextPdfStatus('✨ Fixing punctuation and creating PDF...', 'processing');
    
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
    
    showTextPdfStatus('✅ PDF created successfully! Download started.', 'success');
    
    // Clear inputs after success
    setTimeout(() => {
      pdfTitle.value = '';
      pdfText.value = '';
      textPdfStatus.classList.add('hidden');
    }, 3000);
    
  } catch (error) {
    console.error('Text to PDF error:', error);
    showTextPdfStatus(`❌ ${error.message}`, 'error');
  } finally {
    createPdfBtn.disabled = false;
    createPdfBtn.textContent = '✨ Create PDF';
  }
});

function showTextPdfStatus(message, type) {
  textPdfStatus.innerHTML = message;
  textPdfStatus.className = 'text-pdf-status ' + type;
  textPdfStatus.classList.remove('hidden');
  
  if (type === 'error') {
    setTimeout(() => {
      textPdfStatus.classList.add('hidden');
    }, 5000);
  }
}

