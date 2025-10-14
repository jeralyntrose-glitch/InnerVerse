// Google Drive Picker Integration
let pickerInited = false;
let gisInited = false;
let tokenClient;
let accessToken = null;

const CLIENT_ID = ''; // Will be loaded from backend
const API_KEY = ''; // Will be loaded from backend
const DISCOVERY_DOC = 'https://www.googleapis.com/discovery/v1/apis/drive/v3/rest';
const SCOPES = 'https://www.googleapis.com/auth/drive.readonly';

// Load the Google API scripts
function loadGoogleAPIs() {
  const gapiScript = document.createElement('script');
  gapiScript.src = 'https://apis.google.com/js/api.js';
  gapiScript.async = true;
  gapiScript.defer = true;
  gapiScript.onload = gapiLoaded;
  document.head.appendChild(gapiScript);

  const gisScript = document.createElement('script');
  gisScript.src = 'https://accounts.google.com/gsi/client';
  gisScript.async = true;
  gisScript.defer = true;
  gisScript.onload = gisLoaded;
  document.head.appendChild(gisScript);
}

function gapiLoaded() {
  gapi.load('client:picker', initializePicker);
}

async function initializePicker() {
  await gapi.client.load(DISCOVERY_DOC);
  pickerInited = true;
}

function gisLoaded() {
  // We'll use server-side OAuth instead
  gisInited = true;
}

// Open Google Drive Picker
async function openGoogleDrivePicker() {
  try {
    // Get access token from server
    const tokenResponse = await fetch('/api/gdrive-token');
    const tokenData = await tokenResponse.json();
    
    if (!tokenData.access_token) {
      alert('❌ Google Drive not connected. Please contact support.');
      return;
    }

    accessToken = tokenData.access_token;

    // Create and render the picker
    const picker = new google.picker.PickerBuilder()
      .addView(new google.picker.DocsView()
        .setIncludeFolders(true)
        .setMimeTypes('application/pdf'))
      .setOAuthToken(accessToken)
      .setDeveloperKey(API_KEY || 'fallback-key')
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

// Handle file selection from picker
async function pickerCallback(data) {
  if (data.action === google.picker.Action.PICKED) {
    const files = data.docs.filter(doc => doc.mimeType === 'application/pdf');
    
    if (files.length === 0) {
      alert('❌ Please select PDF files only.');
      return;
    }

    // Download and process each file
    for (const file of files) {
      await downloadAndProcessGDriveFile(file.id, file.name);
    }
  }
}

// Download file from Google Drive and process it
async function downloadAndProcessGDriveFile(fileId, fileName) {
  try {
    const response = await fetch(`/api/gdrive-download/${fileId}`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Download failed');
    }

    // Process the base64 PDF data
    const fileObj = { name: fileName, base64: data.pdf_base64 };
    
    // Trigger the same upload flow as regular files
    if (window.processGDriveFile) {
      window.processGDriveFile(fileObj);
    }
  } catch (error) {
    console.error('Download error:', error);
    alert(`❌ Failed to download ${fileName}: ${error.message}`);
  }
}

// Initialize on load
if (typeof gapi === 'undefined' || typeof google === 'undefined') {
  loadGoogleAPIs();
}

// Export for use in main script
window.openGoogleDrivePicker = openGoogleDrivePicker;
