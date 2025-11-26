# 🔍 DEBUG CHECKLIST - Phase 1 Refactor

## Variables That Must Exist

### ✅ Verified Present:
- [x] `selectedImages` - Added back at line ~1796
- [x] `conversationId` - Window property → appState.conversationId
- [x] `isStreaming` - Window property → appState.isStreaming  
- [x] `currentAbortController` - Window property → appState.currentAbortController
- [x] `allConversations` - Window property → appState.allConversations
- [x] `uploadedImages` - Window property → appState.uploadedImages

### ✅ Verified Present (Scroll-related):
- [x] `isUserPinnedToBottom` - Window property → scrollManager.state.isPinnedToBottom
- [x] `hardScrollLock` - Window property → scrollManager.state.hardLocked
- [x] `scrollLockUntil` - Window property → scrollManager.state.lockUntil
- [x] `lastInputEndTime` - Window property → scrollManager.state.lastInputEndTime
- [x] `suppressScrollEvents` - Window property → scrollManager.state.suppressEvents
- [x] `conversationScrollPositions` - Window property → scrollManager.state.conversationPositions

## Functions That Must Work

### Critical Functions:
- [ ] `loadAllConversations()` - Sets allConversations, calls renderSidebar()
- [ ] `renderSidebar()` - Renders folder structure
- [ ] `sendMessage()` - Sends user message
- [ ] `scrollToBottom()` - Wrapper for scrollManager.toBottom()
- [ ] scrollToBottomBtn click handler - Uses lastInputEndTime

## Initialization Order

1. ✅ SCROLL_CONFIG constant
2. ✅ ScrollManager class definition
3. ✅ StateManager class definition  
4. ✅ EventManager class definition
5. ✅ Folder configuration (FOLDERS array)
6. ✅ DOM element selection (burgerMenu, sidebar, messages, etc.)
7. ✅ ScrollManager initialization (AFTER messages element exists)
8. ✅ ScrollManager compatibility aliases
9. ✅ StateManager compatibility aliases
10. ✅ Event listeners (burger menu, sidebar, theme, etc.)
11. ✅ Async IIFE initialization (loadAllConversations, etc.)

## Browser Console Test

Open browser console and run:
```javascript
console.log('=== STATE CHECK ===');
console.log('conversationId:', typeof conversationId, conversationId);
console.log('isStreaming:', typeof isStreaming, isStreaming);
console.log('selectedImages:', typeof selectedImages, selectedImages);
console.log('allConversations:', typeof allConversations, allConversations?.length);
console.log('scrollManager:', typeof scrollManager);
console.log('appState:', typeof appState);
console.log('=== END CHECK ===');
```

Expected output:
- conversationId: number or null
- isStreaming: boolean
- selectedImages: object (array)
- allConversations: object (array) with length
- scrollManager: object
- appState: object

## Next Steps

If variables are undefined:
1. Check browser console for "ReferenceError" or "is not defined"
2. Check initialization order
3. Verify window properties are set before use

If functions don't execute:
1. Check browser console for errors
2. Verify event listeners are attached
3. Check if DOM elements exist when listeners attach

