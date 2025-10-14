/* Reset */
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background-color: #f9fafb;
  color: #1a1a1a;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 20px;
  position: relative;
}

.page-wrapper {
  text-align: center;
  max-width: 500px;
  width: 100%;
}

.branding {
  margin-bottom: 20px;
}

.brand-title {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 1px;
  margin-bottom: 5px;
}

.tagline {
  font-size: 14px;
  color: #555;
  margin-bottom: 25px;
}

.drop-area {
  border: 2px dashed #ccc;
  padding: 30px 20px;
  border-radius: 12px;
  background-color: #fff;
  transition: border-color 0.3s ease;
}

.drop-area.dragover {
  border-color: #4f46e5;
  background-color: #eef2ff;
}

.drop-text {
  font-size: 16px;
  margin-bottom: 10px;
}

.or-text {
  display: block;
  font-size: 13px;
  color: #888;
  margin-bottom: 10px;
}

.custom-file-upload {
  background-color: #f0f0f0;
  border: 1px solid #ccc;
  padding: 8px 18px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  display: inline-block;
  transition: background-color 0.2s ease;
}

.custom-file-upload:hover {
  background-color: #e0e0e0;
}

input[type="file"] {
  display: none;
}

.status {
  margin-top: 20px;
  font-size: 14px;
  color: #444;
  line-height: 1.6;
}

.status code {
  background: #e5e7eb;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: monospace;
  font-size: 13px;
}

/* Floating Chat Button */
.chat-toggle {
  position: fixed;
  bottom: 20px;
  right: 20px;
  background-color: #4f46e5;
  color: white;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  cursor: pointer;
  box-shadow: 0 4px 8px rgba(0,0,0,0.2);
  z-index: 1000;
}

/* Chat Container */
.chat-container {
  position: fixed;
  bottom: 80px;
  right: 20px;
  width: 300px;
  max-height: 400px;
  background-color: #ffffff;
  border: 1px solid #ccc;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 1001;
}

.hidden {
  display: none;
}

.chat-header {
  background-color: #4f46e5;
  color: white;
  padding: 10px;
  font-weight: bold;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-header button {
  background: none;
  border: none;
  color: white;
  font-size: 18px;
  cursor: pointer;
}

/* Chat Log */
.chat-log {
  flex: 1;
  padding: 10px;
  overflow-y: auto;
  background-color: #f4f4f4;
  font-size: 12px;
}

.chat-message {
  margin-bottom: 10px;
  padding: 8px 12px;
  border-radius: 12px;
  max-width: 80%;
  clear: both;
  word-wrap: break-word;
  line-height: 1.4;
}

.chat-message.user {
  background-color: #d1e7ff;
  align-self: flex-end;
  float: right;
}

.chat-message.bot {
  background-color: #e5e5ea;
  align-self: flex-start;
  float: left;
}

/* Chat input area */
.chat-input-area {
  display: flex;
  padding: 8px;
  border-top: 1px solid #ccc;
  background-color: #fff;
}

.chat-input-area input {
  flex: 1;
  padding: 8px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 6px;
}

.chat-input-area button {
  margin-left: 6px;
  padding: 8px 12px;
  background-color: #4f46e5;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.chat-input-area button:hover {
  background-color: #4338ca;
}

/* Mobile responsive tweaks */
@media (max-width: 480px) {
  .chat-container {
    right: 10px;
    width: 95%;
  }

  .chat-toggle {
    right: 10px;
    bottom: 10px;
  }

  .chat-message {
    font-size: 12px;
  }
}
