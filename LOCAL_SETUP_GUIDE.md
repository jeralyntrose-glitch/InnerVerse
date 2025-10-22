# 🧠 InnerVerse - Local YouTube Transcriber Setup

Run YouTube transcriptions on your laptop to avoid IP blocks!

---

## 📦 What You Need

1. **Python 3.8+** (probably already installed on Mac)
2. **Your OpenAI API Key**
3. A few tools (we'll install these)

---

## 🚀 Setup Instructions

### Step 1: Download the Script

1. Download `local_youtube_transcriber.py` from this Repl
2. Save it somewhere easy to find (like your Desktop or Documents folder)

### Step 2: Install Python Packages

Open **Terminal** (Mac) or **Command Prompt** (Windows) and run:

```bash
pip install openai yt-dlp reportlab pydub
```

If `pip` doesn't work, try:
```bash
pip3 install openai yt-dlp reportlab pydub
```

### Step 3: Install ffmpeg

**Mac (easiest way):**
```bash
brew install ffmpeg
```

Don't have Homebrew? Install it first:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Windows:**
1. Download from: https://ffmpeg.org/download.html
2. Follow installation instructions

### Step 4: Set Your OpenAI API Key

**Mac/Linux:**
```bash
export OPENAI_API_KEY='sk-your-key-here'
```

**Windows:**
```cmd
set OPENAI_API_KEY=sk-your-key-here
```

💡 **Tip:** Get your API key from: https://platform.openai.com/api-keys

---

## ▶️ How to Use

### Option 1: Run with Command Line

```bash
cd /path/to/folder/with/script
python local_youtube_transcriber.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Option 2: Run Interactively

```bash
python local_youtube_transcriber.py
```

Then paste the YouTube URL when prompted.

---

## 📂 Output

PDFs are saved in a `transcriptions/` folder in the same directory as the script.

---

## 💰 Cost

Same as before: **~$0.006 per minute** of video

A 30-minute video costs about **$0.18**

---

## ❓ Troubleshooting

### "yt-dlp not found"
```bash
pip install yt-dlp
```

### "ffmpeg not found"
Make sure ffmpeg is installed (see Step 3 above)

### "OPENAI_API_KEY not found"
You need to set your API key every time you open a new Terminal window.

**To set it permanently on Mac:**
Add this line to `~/.zshrc` or `~/.bash_profile`:
```bash
export OPENAI_API_KEY='sk-your-key-here'
```

### YouTube still blocking?
This shouldn't happen locally since your cookies match your home IP! But if it does:
1. Make sure you're on your home WiFi (not VPN)
2. Clear your browser cache
3. Try a different video

---

## 🔄 To Upload to InnerVerse

After transcribing locally, you can manually upload the generated PDF to your InnerVerse app on Replit!

Just use the normal PDF upload button. Your local transcription will be tagged and added to your library automatically. 💜

---

## 🎯 Benefits of Running Locally

✅ No IP blocks (your cookies match your home IP)  
✅ Faster downloads (no datacenter limits)  
✅ Works with any video (age-restricted, members-only, etc.)  
✅ No proxy costs  

---

Need help? Let me know! 🚀
