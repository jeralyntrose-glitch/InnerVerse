# 🐛 Bug Solutions & Patterns

**Purpose**: Centralized reference for bug fixes, solutions, and patterns to help solve future issues faster.

**Last Updated**: 2025-12-06

---

## 📋 Table of Contents

- [UnboundLocalError with Import Statements](#unboundlocalerror-with-import-statements)
- [CSS Scrolling Issues](#css-scrolling-issues)
- [Season Search Problems](#season-search-problems)
- [Dark Mode Icon Visibility](#dark-mode-icon-visibility)
- [Overflow Hidden Cutting Off Content](#overflow-hidden-cutting-off-content)
- [Patterns & Best Practices](#patterns--best-practices)

---

## UnboundLocalError with Import Statements

### Problem
Functions crash with `UnboundLocalError: cannot access local variable 'X' where it is not associated with a value` where X is a module name (e.g., `json`, `openai_client`).

### Root Cause
Python's variable scoping rules create this error when:
1. A variable/module is **used** in a function
2. Then **imported/assigned** later in the SAME function
3. Python sees the future import/assignment and treats the name as LOCAL throughout the entire function
4. When the code tries to use it before the import/assignment, it's "unbound" (not yet assigned)

**Example that causes the bug:**
```python
def my_function():
    # Line 50: Uses json (but Python knows json will be imported at line 100)
    data = json.dumps({"status": "searching"})  # ❌ UnboundLocalError!
    
    # ... 50 lines of code ...
    
    # Line 100: Import happens too late
    import json  # Python marks 'json' as LOCAL from here
```

### Solution Pattern

**Move all imports to the TOP of the function:**

```python
def my_function():
    import json  # ✅ Import FIRST, before any usage
    
    # Now safe to use json anywhere in the function
    data = json.dumps({"status": "searching"})  # ✅ Works!
    
    # ... rest of function ...
```

**For module-level objects (like clients), initialize at module level:**

```python
# At top of file (module level)
from openai import OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# In function
def my_function():
    # Use the module-level client directly
    response = openai_client.embeddings.create(...)  # ✅ Works!
```

### Real Examples Fixed

**1. `claude_api.py` - `chat_with_claude_streaming()` function:**

❌ **Before (broken):**
```python
def chat_with_claude_streaming(...):
    # Line 989: Uses json
    yield "data: " + '{"error": "..."}\n\n'
    
    # Line 1057: Uses json.dumps()
    yield "data: " + json.dumps({"error": error_msg}) + "\n\n"
    
    # Line 1083: Import happens here (TOO LATE)
    import json
    yield "data: " + json.dumps({"chunk": text}) + "\n\n"
```

✅ **After (fixed):**
```python
def chat_with_claude_streaming(...):
    import json  # 🐛 FIX: Import at function top
    
    # Now all uses of json work correctly
    yield "data: " + '{"error": "..."}\n\n'
    yield "data: " + json.dumps({"error": error_msg}) + "\n\n"
    yield "data: " + json.dumps({"chunk": text}) + "\n\n"
```

**2. `claude_api.py` - `query_innerverse_local()` function:**

❌ **Before (broken):**
```python
def query_innerverse_local(question: str, top_k: int = 20):
    # Line 1379: Uses openai_client
    embedding_response = openai_client.embeddings.create(...)
    
    # Line 1470: Reassigns openai_client (TOO LATE)
    openai_client = get_openai_client()  # ❌ Makes it LOCAL
```

✅ **After (fixed):**
```python
# Module-level initialization (at top of file)
from services.openai_client import get_openai_client
openai_client = get_openai_client()

def query_innerverse_local(question: str, top_k: int = 20):
    # Use module-level client directly
    embedding_response = openai_client.embeddings.create(...)  # ✅ Works!
```

### Key Learnings

1. **Always import at the TOP** of functions (or module level)
2. **Never import in the MIDDLE** of a function after using the module
3. **Python scoping is function-wide** - An assignment anywhere makes a name LOCAL everywhere
4. **Module-level initialization** is better for clients/connections that are reused
5. **Check for duplicate imports** - Remove redundant imports after fixing

### How to Detect This Bug

**Error message pattern:**
```
UnboundLocalError: cannot access local variable 'X' where it is not associated with a value
```

**Where X is:**
- `json` - Most common
- `openai_client` - Client objects
- Any module name

**How to find it:**
1. Search for the variable name in the function
2. Find where it's FIRST used
3. Find where it's IMPORTED/ASSIGNED
4. If import/assignment comes AFTER usage → BUG!

### Prevention Checklist

✅ **Always:**
- Import modules at the TOP of functions (or module level)
- Initialize clients at module level when possible
- Test functions thoroughly after adding imports

❌ **Never:**
- Import in the middle of a function
- Import inside try/except blocks unless necessary
- Re-assign module-level variables inside functions

### Related Files
- `claude_api.py` - `chat_with_claude_streaming()` function (lines 982-1222)
- `claude_api.py` - `query_innerverse_local()` function (lines 1290-1545)

---

## CSS Scrolling Issues

### Problem
Document Library section not scrolling when many documents are present.

### Root Cause
- CSS class selector didn't match HTML element
- Missing `max-height` and `overflow-y: auto` on the correct selector
- Parent containers might prevent scrolling

### Solution Pattern

```css
/* Always target both class AND ID selectors */
.documents-list,
#tagged-documents-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 520px !important; /* Force with !important if needed */
  overflow-y: auto !important;
  overflow-x: hidden;
  padding-right: 8px; /* Space for scrollbar */
  position: relative;
}

/* Ensure parent containers don't block scrolling */
.documents-section {
  position: relative;
  width: 100%;
  /* Don't add overflow: hidden here */
}
```

### Key Learnings
1. **Check both class and ID selectors** - HTML might use both
2. **Use `!important` sparingly** - Only when overriding conflicting styles
3. **Parent containers matter** - Ensure parents don't have `overflow: hidden`
4. **Update CSS cache version** - Change `?v=XX` in HTML to force browser refresh
5. **Test with hard refresh** - Ctrl+Shift+R / Cmd+Shift+R

### Related Files
- `static/style.css` - `.documents-list` styles
- `uploader.html` - Document Library HTML structure

---

## Season Search Problems

### Problem
Chat service couldn't find Season 3 content (or any specific season) even though it exists in Pinecone.

### Root Cause
- Chat service wasn't using query intelligence service
- No metadata filters applied to Pinecone queries
- Season extraction patterns were too narrow

### Solution Pattern

```python
# 1. Import query intelligence
from src.services.query_intelligence import analyze_and_filter, rerank_results

# 2. Analyze query to extract season and build filters
analysis = analyze_and_filter(query)
pinecone_filter = analysis.get('pinecone_filter', {})

# 3. Apply filter to Pinecone query
query_params = {
    "vector": query_vector,
    "top_k": recommended_top_k,
    "include_metadata": True
}

if pinecone_filter:
    query_params["filter"] = pinecone_filter

# 4. Query and re-rank
results = pinecone_index.query(**query_params)
ranked_matches = rerank_results(results.matches, query, analysis)
```

### Season Extraction Patterns

```python
# Match multiple formats:
# - "Season 3", "season 3", "season3"
# - "S3", "s3"
# - "[3]", "[3.1]"

match = re.search(r'season\s*(\d+)', question, re.IGNORECASE)
# OR
match = re.search(r'\bS(\d+)\b', question, re.IGNORECASE)
# OR
match = re.search(r'\[(\d+)', question)
```

### Key Learnings
1. **Always use query intelligence** - Don't do raw Pinecone queries
2. **Extract entities first** - Season, types, functions, etc.
3. **Apply metadata filters** - Much more accurate than pure semantic search
4. **Re-rank results** - Boost exact matches (season, type, etc.)
5. **Add fallback logic** - If filtered query returns nothing, try without filter to diagnose

### Related Files
- `src/services/chat_service.py` - `query_pinecone_organized()` method
- `src/services/query_intelligence.py` - Entity extraction and filtering

---

## Dark Mode Icon Visibility

### Problem
Icons (burger menu, plus button, scroll arrow) too dark in dark mode, hard to see.

### Root Cause
- Inline SVG `stroke` colors overriding CSS
- CSS selectors not specific enough
- Missing dark mode overrides

### Solution Pattern

```css
/* Target SVG elements specifically */
.burger-menu svg,
.burger-menu svg path,
.burger-menu svg .burger-icon-path {
  stroke: #2d2d2d !important; /* Light mode */
}

/* Dark mode override */
[data-theme="dark"] .burger-menu svg,
[data-theme="dark"] .burger-menu svg path,
[data-theme="dark"] .burger-menu svg .burger-icon-path {
  stroke: #e0e0e0 !important; /* Light gray in dark mode */
}
```

### Key Learnings
1. **Target SVG paths directly** - Inline styles on `<path>` elements need specific selectors
2. **Use `!important` for overrides** - Inline styles have high specificity
3. **Test both light and dark modes** - Always verify theme switching
4. **Use consistent color values** - `#e0e0e0` for light gray, `#2d2d2d` for dark gray

### Related Files
- `templates/innerverse.html` - Icon SVG elements and CSS

---

## Overflow Hidden Cutting Off Content

### Problem
Content in modal cards (Q&A pairs in Review modal) appeared to be missing. Only the header was visible, text below it was invisible even though console logs showed the HTML was correctly generated with the text content.

### Root Cause
CSS `overflow: hidden` on the parent container (`.training-pair-card`) was physically cutting off content that extended beyond the container's set `min-height`. The text WAS in the DOM but the container wouldn't expand to show it.

### Symptoms
- Console shows HTML is correct with text content
- Only card header visible
- Faint gray rectangle visible below header (the clipped content)
- Different approaches (template literals, DOM manipulation, inline styles) all "fail"

### Solution Pattern

❌ **Before (broken):**
```css
.training-pair-card {
  background: #111827;
  border: 1px solid #374151;
  border-radius: 12px;
  overflow: hidden;      /* ← CULPRIT! */
  min-height: 120px;     /* ← Fixed height prevents growth */
}
```

✅ **After (fixed):**
```css
.training-pair-card {
  background: #111827;
  border: 1px solid #374151;
  border-radius: 12px;
  overflow: visible;     /* ← Allow content to show */
  min-height: auto;      /* ← Allow container to grow */
}
```

### Key Learnings
1. **`overflow: hidden` hides content** - It clips anything beyond the container boundaries
2. **Fixed heights prevent growth** - Use `min-height: auto` to allow expansion
3. **Console debugging is essential** - Verify HTML is correct before assuming JS bug
4. **Check parent containers** - The issue might not be on the element itself
5. **Gray rectangles = clipped content** - If you see partial elements, suspect overflow

### How to Detect This Bug
- Content "not showing" but console shows correct HTML
- Partial elements visible (corners, edges of boxes)
- Different rendering approaches all fail the same way
- Edit modal (using `.value`) works but display divs don't

### Related Files
- `uploader.html` - `.training-pair-card` CSS styles
- Any modal or card component with `overflow: hidden`

---

## Patterns & Best Practices

### CSS Specificity Issues

**Problem**: Styles not applying despite correct selectors.

**Solution Checklist**:
1. ✅ Check if element has both class AND ID - target both
2. ✅ Verify parent containers don't have conflicting styles
3. ✅ Use browser DevTools to inspect computed styles
4. ✅ Check for inline styles that override CSS
5. ✅ Update CSS cache version in HTML (`?v=XX`)
6. ✅ Hard refresh browser (Ctrl+Shift+R)

### Pinecone Query Issues

**Problem**: Not finding content that exists in Pinecone.

**Solution Checklist**:
1. ✅ Use query intelligence service (don't do raw queries)
2. ✅ Extract entities (season, types, functions) from query
3. ✅ Build metadata filters using `FilterBuilder`
4. ✅ Apply filters to Pinecone query
5. ✅ Re-rank results to boost exact matches
6. ✅ Add fallback: try without filter if filtered query returns nothing
7. ✅ Check metadata format in Pinecone (strings vs numbers, arrays vs single values)

### Debugging CSS Issues

**Pattern**:
```css
/* Add temporary border to see element boundaries */
.element {
  border: 2px solid red !important; /* Debug only */
}

/* Check if element is actually visible */
.element {
  opacity: 0.5 !important; /* Debug only */
  background: yellow !important; /* Debug only */
}
```

### Debugging JavaScript Issues

**Pattern**:
```javascript
// Add console logs at key points
console.log('🔍 [DEBUG] Variable value:', variable);
console.log('🔍 [DEBUG] Element:', element);
console.log('🔍 [DEBUG] Event:', event);

// Check if function is being called
console.log('🔍 [DEBUG] Function called:', functionName);
```

---

## Contributing

When you fix a bug:

1. **Document it here** - Add a new section with:
   - Problem description
   - Root cause
   - Solution pattern (code examples)
   - Key learnings
   - Related files

2. **Use clear structure**:
   ```markdown
   ## [Bug Name]
   
   ### Problem
   [Description]
   
   ### Root Cause
   [Why it happened]
   
   ### Solution Pattern
   [Code example]
   
   ### Key Learnings
   [Takeaways]
   ```

3. **Update date** - Change "Last Updated" at top of file

---

## Quick Reference

### Common CSS Issues
- **Scrolling not working**: Check `overflow-y: auto`, `max-height`, parent containers
- **Styles not applying**: Check specificity, inline styles, cache version
- **Dark mode issues**: Always test both themes, use `[data-theme="dark"]` selector
- **Content cut off/invisible**: Check for `overflow: hidden` on parent containers, change to `overflow: visible`

### Common JavaScript Issues
- **Event listeners not firing**: Check element exists, event delegation, timing
- **API calls failing**: Check network tab, CORS, authentication
- **State not updating**: Check async/await, promise handling, React state

### Common Backend Issues
- **Database queries failing**: Check connection pooling, transaction handling
- **API endpoints not found**: Check route registration, URL patterns
- **Authentication issues**: Check CSRF tokens, session management

---

**Remember**: When in doubt, check browser DevTools, server logs, and test in incognito mode to rule out cache issues.

