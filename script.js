const dropArea = document.getElementById('drop-area');
const fileInput = document.getElementById('fileElem');
const status = document.getElementById('status');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const chatMessages = document.getElementById('chat-messages');

let currentDocumentId = null;

// === Upload Logic ===
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
  const files = e.dataTransfer.files;
  handleFiles(files);
});

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
        navigator.clipboard.writeText(result.document_id).then(() => {
          status.innerHTML += '<br>📋 Document ID copied to clipboard!';
        });
      } else {
        throw new Error(result.error || 'Upload failed');
      }
    } catch (err) {
      status.textContent = `❌ Upload failed: ${err.message}`;
    }
  };

  reader.readAsDataURL(file);
}

// === Floating Chat Logic ===
const chatToggle = document.getElementById("chat-toggle");
const chatWindow = document.getElementById("chat-float");
const closeChat = document.getElementById("close-chat");

chatToggle.addEventListener("click", () => {
  chatWindow.classList.toggle("hidden");
});

closeChat.addEventListener("click", () => {
  chatWindow.classList.add("hidden");
});

sendBtn.addEventListener("click", sendChat);
chatInput.addEventListener("keypress", (e) => {
  if (e.key === "Enter") sendChat();
});

function appendMessage(text, sender = "user") {
  const div = document.createElement("div");
  div.className = sender === "user" ? "user-msg" : "bot-msg";
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function sendChat() {
  const question = chatInput.value.trim();
  if (!question) return;

  if (!currentDocumentId) {
    appendMessage('⚠️ Please upload a PDF first.', 'bot');
    chatInput.value = '';
    return;
  }

  appendMessage(question, "user");
  appendMessage("🧠 Thinking...", "bot");

  try {
    const res = await fetch("/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        document_id: currentDocumentId,
        question 
      })
    });

    const data = await res.json();
    const answer = data.answer || "No response.";

    const botMessages = document.querySelectorAll(".bot-msg");
    const lastBotMsg = botMessages[botMessages.length - 1];
    lastBotMsg.textContent = answer;

  } catch (err) {
    const botMessages = document.querySelectorAll(".bot-msg");
    const lastBotMsg = botMessages[botMessages.length - 1];
    lastBotMsg.textContent = "❌ Error: " + err.message;
  }

  chatInput.value = '';
}
