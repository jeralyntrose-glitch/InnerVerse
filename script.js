// Upload functionality
const dropArea = document.getElementById('drop-area');
const fileInput = document.getElementById('fileElem');
const status = document.getElementById('status');

// Chat functionality
const chatToggle = document.getElementById('chat-toggle');
const chatContainer = document.getElementById('chat-container');
const chatClose = document.getElementById('chat-close');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const chatLog = document.getElementById('chat-log');

let currentDocumentId = null;

// === UPLOAD SECTION ===

// Drag events for file upload
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

// Drop handler
dropArea.addEventListener('drop', e => {
  const files = e.dataTransfer.files;
  handleFiles(files);
});

// File input handler
fileInput.addEventListener('change', e => {
  const files = e.target.files;
  handleFiles(files);
});

function handleFiles(files) {
  const file = files[0];
  if (!file || file.type !== 'application/pdf') {
    status.textContent = '❌ Please upload a valid PDF file.';
    return;
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
        status.innerHTML = `
          ✅ <strong>${file.name}</strong> uploaded successfully.<br>
          🆔 Document ID: <code>${result.document_id}</code><br>
          📦 Chunks stored: ${result.chunks_count}
        `;
        
        // Copy document ID to clipboard
        navigator.clipboard.writeText(result.document_id).then(() => {
          status.innerHTML += '<br>📋 Document ID copied to clipboard!';
        });

        // Show chat toggle if hidden
        chatToggle.style.display = 'flex';
      } else {
        throw new Error(result.error || 'Upload failed');
      }
    } catch (err) {
      status.textContent = `❌ Upload failed: ${err.message}`;
    }
  };

  reader.readAsDataURL(file);
}

// === CHAT SECTION ===

// Toggle chat window
chatToggle.addEventListener('click', () => {
  chatContainer.classList.toggle('hidden');
});

// Close chat window
chatClose.addEventListener('click', () => {
  chatContainer.classList.add('hidden');
});

// Send message on button click
sendBtn.addEventListener('click', askQuestion);

// Send message on Enter key
chatInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    askQuestion();
  }
});

async function askQuestion() {
  const question = chatInput.value.trim();
  if (!question) return;

  if (!currentDocumentId) {
    addChatMessage('bot', '⚠️ Please upload a PDF first before asking questions.');
    return;
  }

  // Add user message to chat
  addChatMessage('user', question);
  chatInput.value = '';

  // Show thinking message
  const thinkingMsg = addChatMessage('bot', '🧠 Thinking...');
  sendBtn.disabled = true;

  try {
    const res = await fetch('/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ 
        document_id: currentDocumentId,
        question: question 
      })
    });

    const data = await res.json();
    
    if (res.ok) {
      // Replace thinking message with actual response
      thinkingMsg.textContent = data.answer || 'No response.';
    } else {
      throw new Error(data.error || 'Query failed');
    }
  } catch (err) {
    thinkingMsg.textContent = '❌ Error: ' + err.message;
  }

  sendBtn.disabled = false;
}

function addChatMessage(type, text) {
  const msgDiv = document.createElement('div');
  msgDiv.classList.add('chat-message', type);
  msgDiv.textContent = text;
  chatLog.appendChild(msgDiv);
  chatLog.scrollTop = chatLog.scrollHeight;
  return msgDiv;
}
