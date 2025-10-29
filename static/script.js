/* ====================================
   AXIS MIND - UPLOADER SCRIPT
   Complete functionality for file uploads, chat, and integrations
   ==================================== */

(function() {
  'use strict';

  // === GLOBAL STATE ===
  let uploadQueue = [];
  let uploadStats = {
    uploaded: 0,
    completed: 0,
    errors: 0
  };

  // === THEME TOGGLE ===
  const themeToggle = document.getElementById('theme-toggle');
  const sunIcon = themeToggle.querySelector('.sun-icon');
  const moonIcon = themeToggle.querySelector('.moon-icon');

  function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (savedTheme === 'light') {
      document.body.classList.add('light-theme');
      sunIcon.classList.add('hidden');
      moonIcon.classList.remove('hidden');
    }
  }

  themeToggle.addEventListener('click', () => {
    document.body.classList.toggle('light-theme');
    sunIcon.classList.toggle('hidden');
    moonIcon.classList.toggle('hidden');
    
    const newTheme = document.body.classList.contains('light-theme') ? 'light' : 'dark';
    localStorage.setItem('theme', newTheme);
  });

  // === UTILITY FUNCTIONS ===
  function showError(message) {
    const modal = document.getElementById('error-modal');
    const messageEl = document.getElementById('error-modal-message');
    messageEl.textContent = message;
    modal.classList.remove('hidden');
  }

  function hideError() {
    document.getElementById('error-modal').classList.add('hidden');
  }

  function updateUploadStats() {
    document.getElementById('count-uploaded').textContent = uploadStats.uploaded;
    document.getElementById('count-completed').textContent = uploadStats.completed;
    document.getElementById('count-errors').textContent = uploadStats.errors;
    
    const section = document.getElementById('upload-status-section');
    if (uploadStats.uploaded > 0) {
      section.classList.remove('hidden');
    }
  }

  function createUploadItem(file) {
    const item = document.createElement('div');
    item.className = 'upload-item';
    item.id = `upload-${file.name.replace(/[^a-z0-9]/gi, '_')}`;
    
    item.innerHTML = `
      <div class="upload-item-header">
        <span class="upload-filename">${file.name}</span>
        <span class="upload-status uploading">Uploading...</span>
      </div>
      <div class="progress-bar-container">
        <div class="progress-bar" style="width: 0%"></div>
      </div>
    `;
    
    document.getElementById('upload-list').appendChild(item);
    return item;
  }

  function updateUploadItem(itemId, status, progress = null) {
    const item = document.getElementById(itemId);
    if (!item) return;
    
    const statusEl = item.querySelector('.upload-status');
    const progressBar = item.querySelector('.progress-bar');
    
    statusEl.className = `upload-status ${status}`;
    
    if (status === 'uploading') {
      statusEl.textContent = 'Uploading...';
      if (progress !== null) {
        progressBar.style.width = `${progress}%`;
      }
    } else if (status === 'completed') {
      statusEl.textContent = '✓ Completed';
      progressBar.style.width = '100%';
    } else if (status === 'error') {
      statusEl.textContent = '✗ Error';
      progressBar.style.width = '100%';
    }
  }

  // === DRAG & DROP FILE UPLOAD ===
  const dropArea = document.getElementById('drop-area');
  const fileInput = document.getElementById('fileElem');

  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, preventDefaults, false);
    document.body.addEventListener(eventName, preventDefaults, false);
  });

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  ['dragenter', 'dragover'].forEach(eventName => {
    dropArea.addEventListener(eventName, () => {
      dropArea.classList.add('highlight');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, () => {
      dropArea.classList.remove('highlight');
    });
  });

  dropArea.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    handleFiles(files);
  });

  fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
  });

  async function handleFiles(files) {
    const fileArray = Array.from(files);
    
    for (const file of fileArray) {
      if (file.type !== 'application/pdf') {
        showError(`${file.name} is not a PDF file. Please upload only PDF files.`);
        continue;
      }
      
      await uploadFile(file);
    }
    
    fileInput.value = '';
  }

  async function uploadFile(file) {
    const itemId = `upload-${file.name.replace(/[^a-z0-9]/gi, '_')}`;
    const uploadItem = createUploadItem(file);
    
    uploadStats.uploaded++;
    updateUploadStats();
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const xhr = new XMLHttpRequest();
      
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percentComplete = (e.loaded / e.total) * 100;
          updateUploadItem(itemId, 'uploading', percentComplete);
        }
      });
      
      xhr.addEventListener('load', () => {
        if (xhr.status === 200) {
          updateUploadItem(itemId, 'completed');
          uploadStats.completed++;
          updateUploadStats();
          
          const response = JSON.parse(xhr.responseText);
          console.log('Upload success:', response);
        } else {
          throw new Error(xhr.responseText || 'Upload failed');
        }
      });
      
      xhr.addEventListener('error', () => {
        updateUploadItem(itemId, 'error');
        uploadStats.errors++;
        updateUploadStats();
        showError(`Failed to upload ${file.name}. Please try again.`);
      });
      
      xhr.open('POST', '/upload');
      xhr.send(formData);
      
    } catch (error) {
      console.error('Upload error:', error);
      updateUploadItem(itemId, 'error');
      uploadStats.errors++;
      updateUploadStats();
      showError(`Error uploading ${file.name}: ${error.message}`);
    }
  }

  // === YOUTUBE TRANSCRIPTION ===
  const youtubeUrl = document.getElementById('youtube-url');
  const transcribeBtn = document.getElementById('transcribe-btn');
  const youtubeStatus = document.getElementById('youtube-status');

  transcribeBtn.addEventListener('click', async () => {
    const url = youtubeUrl.value.trim();
    
    if (!url) {
      showError('Please enter a YouTube URL');
      return;
    }
    
    if (!url.includes('youtube.com') && !url.includes('youtu.be')) {
      showError('Please enter a valid YouTube URL');
      return;
    }
    
    youtubeStatus.classList.remove('hidden', 'success', 'error');
    youtubeStatus.classList.add('loading');
    youtubeStatus.textContent = '🎬 Transcribing video... This may take a minute.';
    transcribeBtn.disabled = true;
    
    try {
      const response = await fetch('/youtube-to-pdf', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ youtube_url: url })
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Transcription failed');
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `youtube_transcript_${Date.now()}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(downloadUrl);
      
      youtubeStatus.classList.remove('loading');
      youtubeStatus.classList.add('success');
      youtubeStatus.textContent = '✓ Transcript downloaded successfully!';
      youtubeUrl.value = '';
      
    } catch (error) {
      console.error('Transcription error:', error);
      youtubeStatus.classList.remove('loading');
      youtubeStatus.classList.add('error');
      youtubeStatus.textContent = `✗ Error: ${error.message}`;
    } finally {
      transcribeBtn.disabled = false;
    }
  });

  // === TEXT TO PDF CONVERSION ===
  const textPdfToggle = document.getElementById('text-pdf-toggle');
  const textPdfContent = document.getElementById('text-pdf-content');
  const createPdfBtn = document.getElementById('create-pdf-btn');
  const pdfTitle = document.getElementById('pdf-title');
  const pdfText = document.getElementById('pdf-text');
  const textPdfProgress = document.getElementById('text-pdf-progress');

  textPdfToggle.addEventListener('click', () => {
    textPdfToggle.classList.toggle('active');
    textPdfContent.classList.toggle('open');
  });

  createPdfBtn.addEventListener('click', async () => {
    const title = pdfTitle.value.trim();
    const text = pdfText.value.trim();
    
    if (!text) {
      showError('Please enter some text to convert to PDF');
      return;
    }
    
    textPdfProgress.classList.remove('hidden');
    textPdfProgress.querySelector('.text-pdf-status-text').textContent = 'Creating PDF...';
    textPdfProgress.querySelector('.text-pdf-progress-bar').style.width = '50%';
    createPdfBtn.disabled = true;
    
    try {
      const response = await fetch('/text-to-pdf', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          title: title || 'Document',
          text: text
        })
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'PDF creation failed');
      }
      
      textPdfProgress.querySelector('.text-pdf-progress-bar').style.width = '100%';
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `${title || 'document'}_${Date.now()}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(downloadUrl);
      
      textPdfProgress.querySelector('.text-pdf-status-text').textContent = '✓ PDF created successfully!';
      
      setTimeout(() => {
        textPdfProgress.classList.add('hidden');
        textPdfProgress.querySelector('.text-pdf-progress-bar').style.width = '0%';
        pdfTitle.value = '';
        pdfText.value = '';
      }, 2000);
      
    } catch (error) {
      console.error('PDF creation error:', error);
      textPdfProgress.classList.add('hidden');
      showError(`Failed to create PDF: ${error.message}`);
    } finally {
      createPdfBtn.disabled = false;
    }
  });

  // === DOCUMENT REPORT DOWNLOAD ===
  const downloadReportBtn = document.getElementById('download-report-btn');

  downloadReportBtn.addEventListener('click', async () => {
    downloadReportBtn.disabled = true;
    downloadReportBtn.textContent = '⏳ Generating...';
    
    try {
      const response = await fetch('/documents/report');
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to generate report');
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `document_report_${Date.now()}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(downloadUrl);
      
      downloadReportBtn.textContent = '✓ Downloaded!';
      
      setTimeout(() => {
        downloadReportBtn.textContent = '📄 Download Document Report';
      }, 2000);
      
    } catch (error) {
      console.error('Report download error:', error);
      showError(`Failed to download report: ${error.message}`);
      downloadReportBtn.textContent = '📄 Download Document Report';
    } finally {
      downloadReportBtn.disabled = false;
    }
  });

  // === DELETE ALL FILES ===
  const deleteAllBtn = document.getElementById('delete-all-btn');

  deleteAllBtn.addEventListener('click', async () => {
    if (!confirm('⚠️ Are you sure you want to delete ALL uploaded files? This cannot be undone.')) {
      return;
    }
    
    deleteAllBtn.disabled = true;
    deleteAllBtn.textContent = '⏳ Deleting...';
    
    try {
      const response = await fetch('/documents/all', {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to delete files');
      }
      
      uploadStats = { uploaded: 0, completed: 0, errors: 0 };
      updateUploadStats();
      document.getElementById('upload-list').innerHTML = '';
      document.getElementById('upload-status-section').classList.add('hidden');
      
      deleteAllBtn.textContent = '✓ Deleted!';
      
      setTimeout(() => {
        deleteAllBtn.textContent = '🗑️ Delete All Files';
      }, 2000);
      
    } catch (error) {
      console.error('Delete error:', error);
      showError(`Failed to delete files: ${error.message}`);
      deleteAllBtn.textContent = '🗑️ Delete All Files';
    } finally {
      deleteAllBtn.disabled = false;
    }
  });

  // === CHAT WIDGET ===
  const chatToggle = document.getElementById('chat-toggle');
  const chatContainer = document.getElementById('chat-container');
  const chatClose = document.getElementById('chat-close');
  const chatInput = document.getElementById('chatInput');
  const sendBtn = document.getElementById('sendBtn');
  const chatLog = document.getElementById('chat-log');

  chatToggle.addEventListener('click', () => {
    chatContainer.classList.remove('hidden');
    chatInput.focus();
  });

  chatClose.addEventListener('click', () => {
    chatContainer.classList.add('hidden');
  });

  function addChatMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'chat-message-content';
    contentDiv.textContent = content;
    
    messageDiv.appendChild(contentDiv);
    chatLog.appendChild(messageDiv);
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  async function sendChatMessage() {
    const query = chatInput.value.trim();
    
    if (!query) return;
    
    addChatMessage('user', query);
    chatInput.value = '';
    
    addChatMessage('assistant', 'Searching documents...');
    
    try {
      const response = await fetch('/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query })
      });
      
      if (!response.ok) {
        throw new Error('Query failed');
      }
      
      const data = await response.json();
      
      chatLog.removeChild(chatLog.lastChild);
      addChatMessage('assistant', data.answer || 'No relevant information found.');
      
    } catch (error) {
      console.error('Chat error:', error);
      chatLog.removeChild(chatLog.lastChild);
      addChatMessage('assistant', 'Sorry, there was an error processing your question. Please try again.');
    }
  }

  sendBtn.addEventListener('click', sendChatMessage);
  
  chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      sendChatMessage();
    }
  });

  // === GOOGLE DRIVE PICKER ===
  const gdriveBtn = document.getElementById('gdrive-btn');
  let pickerInited = false;
  let oauthToken = null;

  function onApiLoad() {
    gapi.load('auth2', initAuth);
    gapi.load('picker', () => { pickerInited = true; });
  }

  function initAuth() {
    gapi.auth2.init({
      client_id: 'YOUR_GOOGLE_CLIENT_ID',
      scope: 'https://www.googleapis.com/auth/drive.readonly'
    });
  }

  function createPicker() {
    if (pickerInited && oauthToken) {
      const picker = new google.picker.PickerBuilder()
        .addView(google.picker.ViewId.DOCS)
        .setOAuthToken(oauthToken)
        .setCallback(pickerCallback)
        .build();
      picker.setVisible(true);
    }
  }

  function pickerCallback(data) {
    if (data.action === google.picker.Action.PICKED) {
      const fileId = data.docs[0].id;
      console.log('Selected file:', fileId);
    }
  }

  gdriveBtn.addEventListener('click', () => {
    showError('Google Drive integration requires setup. Please configure your Google API credentials first.');
  });

  // === ERROR MODAL CLOSE ===
  document.getElementById('error-modal-ok').addEventListener('click', hideError);
  
  document.getElementById('error-modal').addEventListener('click', (e) => {
    if (e.target.id === 'error-modal') {
      hideError();
    }
  });

  // === INITIALIZATION ===
  initTheme();
  
  if (typeof gapi !== 'undefined') {
    gapi.load('client:auth2:picker', onApiLoad);
  }

  console.log('🚀 AXIS MIND Uploader initialized');

})();
