# 🔍 Streaming Debug Instructions

## Issue Reported
"Chat isn't streaming the AI response" - text not appearing in real-time

## What I Did

### 1. ✅ Fixed UnboundLocalError (completed)
- Fixed `json` import issue in `claude_api.py`
- Backend streaming code is now working correctly
- Committed in: `b98254b`

### 2. 🔍 Added Debug Logging (just now)
- Added **comprehensive console logging** throughout the streaming flow
- Committed in: `b07c4d8`

**Debug logs will show:**
- 🚀 When request is sent to backend
- 📡 Response status received
- 📖 Stream reading started
- 📦 Raw chunks received (first 100 chars)
- 🔍 Parsed data structure
- ✅ Individual chunks extracted
- 📝 Assistant div creation
- 📊 Full response accumulation
- 🎨 innerHTML updates
- ⚠️ Any fallback paths taken

## Next Steps - TESTING REQUIRED

### Step 1: Deploy Changes

```bash
# Push to GitHub
git push origin main

# Deploy on Replit (should auto-deploy)
# OR manually pull latest changes
```

### Step 2: Open Browser Console

1. Go to `/innerverse` page
2. **Open browser console** (F12 or Cmd+Option+I)
3. Make sure **Console** tab is selected
4. **Clear console** to see fresh logs

### Step 3: Send a Test Message

Send any message (e.g., "Hello" or "What is INFJ?")

### Step 4: Check Console Output

**Look for these debug messages (in order):**

```
🚀 [STREAMING DEBUG] Sending message to: /claude/conversations/XXX/message/stream
📡 [STREAMING DEBUG] Response received: 200 true
📖 [STREAMING DEBUG] Starting to read stream...
📦 [STREAMING DEBUG] Raw chunk received: data: {"chunk":"Hello..."}
🔍 [STREAMING DEBUG] Received data: {chunk: "Hello"}
✅ [STREAMING DEBUG] Got chunk: Hello
📝 [STREAMING DEBUG] Creating assistant div
✅ [STREAMING DEBUG] Assistant div created: <div>
📊 [STREAMING DEBUG] Full response length: 5
🎨 [STREAMING DEBUG] Setting innerHTML, cleanHTML length: 10
✅ [STREAMING DEBUG] innerHTML set successfully
```

---

## Diagnosing the Issue

### Scenario 1: No logs at all
**Problem:** JavaScript error preventing function from running
**Fix:** Check for errors in console (red text)

### Scenario 2: Logs stop at "Sending message"
**Problem:** Request failing or timing out
**Fix:** Check network tab for failed requests

### Scenario 3: Logs show "Response received: 500" or "not ok"
**Problem:** Backend error
**Fix:** Check backend logs/terminal for error messages

### Scenario 4: No chunks received (no "Got chunk" logs)
**Problem:** Backend not sending chunks OR chunks malformed
**Fix:** Check backend logs to see if chunks are being yielded

### Scenario 5: Chunks received but "marked/DOMPurify not loaded"
**Problem:** Libraries not loaded
**Fix:** Check if `<script>` tags for marked.js and DOMPurify are present

### Scenario 6: "innerHTML set successfully" but no visible text
**Problem:** CSS hiding content OR assistantDiv not in DOM
**Fix:** Inspect element in browser dev tools to see if content exists

---

## What to Send Me

After testing, please send me:

1. **Console output** (screenshot or copy-paste all the `[STREAMING DEBUG]` logs)
2. **Any error messages** (red text in console)
3. **Network tab** - check the `/message/stream` request:
   - Status code?
   - Response preview (does it show chunks?)
   - Response headers (Content-Type should be `text/event-stream`)

---

## Quick Fixes to Try

### If streaming still doesn't work:

**Fix 1: Hard refresh**
```
Ctrl+Shift+R (Windows/Linux)
Cmd+Shift+R (Mac)
```

**Fix 2: Clear browser cache**
- Open DevTools → Network tab → "Disable cache" checkbox
- Refresh page

**Fix 3: Check if another agent broke something**
```bash
git log --oneline -5
# Look for commits from other agents
# Check what files they changed
```

**Fix 4: Test in incognito mode**
- Rules out browser extension conflicts
- Fresh localStorage/session

---

## Code Analysis

### Backend (claude_api.py) - Should be working ✅

```python
# Line 1087: Yielding chunks correctly
yield "data: " + json.dumps({"chunk": text_chunk}) + "\n\n"
```

### Frontend (innerverse.html) - Should be working ✅

```javascript
// Line 3416-3428: Chunk handling looks correct
if (data.chunk) {
    if (!assistantDiv) {
        assistantDiv = addMessage("assistant", "");
    }
    fullResponse += data.chunk;
    assistantDiv.innerHTML = cleanHTML; // Should update DOM
}
```

### Recent Changes That Might Be Suspicious

**Commit `4b8d96c`** - "fix: chat switching, send button icon color, and voice button functionality"
- Changed 145 lines in `innerverse.html`
- Might have accidentally broken streaming
- Check git diff if needed

---

## Fallback Plan

If debug logs show streaming IS working but text isn't visible:

1. **Check CSS** - maybe content is hidden/transparent
2. **Check DOM** - inspect element to see if HTML exists
3. **Check scroll** - maybe text is there but scrolled off-screen
4. **Check z-index** - maybe something is covering the text

---

## Remove Debug Logs Later

Once we find and fix the issue, remove all `console.log` statements with:

```bash
# Search for all debug logs
grep -n "STREAMING DEBUG" templates/innerverse.html

# Remove them manually or use sed
```

---

**Let me know what you find in the console!** 🔍

