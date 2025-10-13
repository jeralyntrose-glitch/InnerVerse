const uploadBox = document.getElementById("upload-box");
const registry = document.getElementById("registry");
const failedUploads = new Map();

uploadBox.addEventListener("drop", (e) => {
  e.preventDefault();
  const files = e.dataTransfer.files;
  for (const file of files) uploadPDF(file);
});

uploadBox.addEventListener("dragover", (e) => e.preventDefault());

async function uploadPDF(file) {
  try {
    const base64 = await toBase64(file);
    addRegistryEntry(file.name, "Uploading…");

    const response = await fetch("https://axis-of-mind.replit.app/upload-base64", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pdf_base64: base64,
        filename: file.name
      })
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Upload failed");

    const { document_id, chunks_count } = data;
    renderSummaryBubble(file.name, document_id, chunks_count);
    await navigator.clipboard.writeText(document_id);
    showToast("📋 Document ID copied to clipboard");
    updateRegistryEntry(file.name, "✅ Complete", document_id);
  } catch (err) {
    console.error(err);
    failedUploads.set(file.name, file);
    updateRegistryEntry(file.name, "❌ Failed");
    showToast("⚠️ Upload failed: " + err.message);
  }
}

function toBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result.split(",")[1]);
    reader.onerror = (error) => reject(error);
  });
}

function renderSummaryBubble(filename, id, chunks_count) {
  const chat = document.getElementById("chat");
  const bubble = document.createElement("div");
  bubble.classList.add("chat-bubble");
  bubble.innerHTML = `
    <strong>📄 ${filename}</strong><br>
    🧩 Document ID: ${id} <spa<span class="copied"><i class="fas fa-clipboard-check"></i></span>n class="copied">✅</span>
    <hr>
    <p>✅ Uploaded ${chunks_count} chunks to Pinecone</p>
  `;
  chat.appendChild(bubble);
}

  function addRegistryEntry(name, status) {
    const entry = document.createElement("div");
    entry.classList.add("registry-entry", "pending");
    entry.id = name;
    entry.innerHTML = `
      <span class="icon"><i class="fas fa-hourglass-half"></i></span>
      <span class="filename">${name}</span> — 
      <span class="status">${status}</span>
    `;
    registry.appendChild(entry);
  }
}

  function updateRegistryEntry(name, status, id) {
    const entry = document.getElementById(name);
    if (!entry) return;

    const iconSpan = entry.querySelector(".icon");
    const statusSpan = entry.querySelector(".status");

    entry.classList.remove("pending", "failed", "complete");

    if (status.toLowerCase().includes("complete")) {
      entry.classList.add("complete");
      iconSpan.innerHTML = '<i class="fas fa-check-circle"></i>';
    } else if (status.toLowerCase().includes("fail")) {
      entry.classList.add("failed");
      iconSpan.innerHTML = '<i class="fas fa-times-circle"></i>';
    }

    statusSpan.innerText = status;

    if (id && !entry.querySelector(".doc-id")) {
      const idTag = document.createElement("span");
      idTag.classList.add("doc-id");
      idTag.innerHTML = `<i class="fas fa-clipboard"></i> ${id}`;
      entry.appendChild(idTag);
    }
  }

  entry.classList.add("glow");
  setTimeout(() => entry.classList.remove("glow"), 1500);
}

function formatRegistryText(name, status, id = "") {
  let icon = "ℹ️";
  if (status.includes("Uploading")) icon = "⏳";
  if (status.includes("Complete")) icon = "✅";
  if (status.includes("Failed")) icon = "❌";
  return `${icon} ${name} — ${status}${id ? ` (${id})` : ""}`;
}

function showToast(msg) {
  const toast = document.createElement("div");
  toast.classList.add("toast");
  toast.innerText = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}