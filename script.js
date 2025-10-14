const dropArea = document.getElementById('drop-area');
const fileInput = document.getElementById('fileElem');
const status = document.getElementById('status');

// Drag events
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

  status.textContent = `Uploading ${file.name}...`;

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
        status.innerHTML = `
          ✅ <strong>${file.name}</strong> uploaded successfully.<br>
          🆔 Document ID: <code>${result.document_id}</code><br>
          📦 Chunks stored: ${result.chunks_count}
        `;
        
        // Copy document ID to clipboard
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