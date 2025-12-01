# 🐛 Bug Solutions & Patterns

**Purpose**: Centralized reference for bug fixes, solutions, and patterns to help solve future issues faster.

**Last Updated**: 2025-01-XX

---

## 📋 Table of Contents

- [CSS Scrolling Issues](#css-scrolling-issues)
- [Season Search Problems](#season-search-problems)
- [Dark Mode Icon Visibility](#dark-mode-icon-visibility)
- [Patterns & Best Practices](#patterns--best-practices)

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

