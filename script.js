const dropArea = document.getElementById('drop-area');
const fileInput = document.getElementById('fileElem');
const status = document.getElementById('status');
const chatToggle = document.getElementById('chat-toggle');
const chatContainer = document.getElementById('chat-container');
const chatClose = document.getElementById('chat-close');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const chatLog = document.getElementById('chat-log');

let currentDocumentId = null;
let uploadedFiles = new Set(); // Tracks uploaded file names (session-only)

// Drag Events
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

// Handle Drop
dropArea.addEventListener('drop', e => {
  const files = e.dataTransfer.files;
  handleFiles(files);
});

// Handle Browse
fileInput.addEventListener('change', e => {
  const files = e.target.files;
  handleFiles(files);
});

// Upload Logic
function handleFiles(files) {
  const file = files[0];
  if (!file || file.type !== 'application/pdf') {
    status.textContent = '❌ Please upload a valid PDF file.';
    return;
  }

  // Duplicate check (by filename only)
  if (uploadedFiles.has(file.name)) {
    const replace = confirm(`You've already uploaded "${file.name}". Do you want to replace it?`);
    if (!replace) {
      status.textContent = '❌ Upload canceled.';
      return;
    }
  }

  status.textContent = `⏳ Uploading ${file.name}...`;

  const reader = new FileReader();
  reader.onload = async function () {
    const base64Data = reader.result.split(',')[1];

    const payload = {
      filename: file.name,
      pdf_base64: base64Data
    };

    try {
      const res = await fetch('/upload-base64', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      const result = await res.json();

      if (res.ok) {
        currentDocumentId = result.document_id;
        uploadedFiles.add(file.name);

        status.innerHTML = `
          ✅ <strong>${file.name}</strong> uploaded successfully.<br>
          🆔 Document ID: <code>${result.document_id}</code><br>
          📦 Chunks stored: ${result.chunks_count}
        `;

        navigator.clipboard.writeText(result.document_id).then(() => {
          status.innerHTML += '<br>📋 Document ID copied to clipboard!';
        });
      } else {
        throw new Error(result.error || 'Upload failed.');
      }
    } catch (err) {
      status.textContent = `❌ Upload failed: ${err.message}`;
    }
  };

  reader.readAsDataURL(file);
}

// Chat Toggle
chatToggle.addEventListener('click', () => {
  chatContainer.classList.toggle('hidden');
});

chatClose.addEventListener('click', () => {
  chatContainer.classList.add('hidden');
});

// Send Chat Message
sendBtn.addEventListener('click', sendMessage);
chatInput.addEventListener('keypress', e => {
  if (e.key === 'Enter') {
    sendMessage();
  }
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
      body: JSON.stringify({
        document_id: currentDocumentId,
        question: question
      })
    });

    const data = await res.json();

    // Remove "Thinking..." message
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

// Append chat message
function appendMessage(sender, text) {
  const message = document.createElement('div');
  message.classList.add('chat-message', sender);
  message.textContent = text;
  chatLog.appendChild(message);
  chatLog.scrollTop = chatLog.scrollHeight;
}

// Remove "Thinking..." placeholder
function removeLastBotMessage() {
  const messages = chatLog.querySelectorAll('.chat-message.bot');
  if (messages.length > 0) {
    messages[messages.length - 1].remove();
  }
}