# PHASE 7.3: LESSON PAGE - PART 1 (Database + Backend + HTML)

**Project:** InnerVerse - CS Joseph University  
**Phase:** 7.3 of 7 (Part 1 of 3)  
**Goal:** Build complete lesson page - Database & Backend  
**Prerequisites:** Phase 7.1 ✅ Phase 7.2 ✅

---

## ⚠️ CRITICAL INSTRUCTIONS FOR REPLIT AGENT

**READ THIS FIRST:**

1. **DO NOT PROCEED TO PHASE 7.4 until user explicitly approves**
2. **Follow these instructions EXACTLY - no improvisation**
3. **Test each component before moving to next**
4. **If you encounter ANY errors, STOP and report them**
5. **Do not modify Phase 7.1 or 7.2 files**
6. **After completion, provide verification checklist results**
7. **This is Part 1 of 3 - complete this before moving to Part 2**

---

## 🎯 WHAT WE'RE BUILDING

**The Lesson Page** (`/lesson/:id`) - The core learning experience!

**Part 1 Contents:**
- Database schema (lesson_chats table)
- Backend routes (4 new API endpoints)
- HTML structure (complete page layout)

**Features:**
- 3-column layout: Mini sidebar (20%) | Lesson content (40%) | AI Tutor (40%)
- Video player (YouTube embed) OR "Watch on Skool" message
- AI-generated lesson content (from transcript via backend)
- Smart fallback: Shows "coming soon" if transcript not uploaded yet
- Toggle-able transcript viewer (default: closed)
- AI tutor chat interface (persistent per lesson)
- Load/save chat history (persists forever)
- Previous/Next lesson navigation
- Mark lesson complete (update progress)
- Breadcrumb navigation (Dashboard > Season > Lesson)
- Dark/light theme support
- Mobile: Stacked layout with hamburger sidebar

---

## 💾 STEP 1: DATABASE SCHEMA

### 1.1 Create Lesson Chats Table

Add this to your database initialization (or run manually):

```sql
CREATE TABLE IF NOT EXISTS lesson_chats (
  lesson_id INTEGER PRIMARY KEY REFERENCES curriculum(lesson_id) ON DELETE CASCADE,
  messages JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_lesson_chats_lesson_id ON lesson_chats(lesson_id);
CREATE INDEX idx_lesson_chats_updated_at ON lesson_chats(updated_at DESC);
```

**Verification:**
```sql
\d lesson_chats
-- Should show: lesson_id, messages (jsonb), created_at, updated_at

SELECT COUNT(*) FROM lesson_chats;
-- Expected: 0 (empty table initially)
```

**Bug Checks:**
- ✅ Foreign key to curriculum (CASCADE on delete)
- ✅ JSONB for efficient JSON storage
- ✅ Indexes for performance
- ✅ Default empty array for messages

---

## 🔧 STEP 2: BACKEND ROUTES

### 2.1 Add Lesson Page Routes to main.py

**Location:** Add AFTER Phase 7.2 routes (around line 4200)

```python
# ==============================================================================
# PHASE 7.3: LESSON PAGE ROUTES
# ==============================================================================

@app.get("/lesson/{lesson_id}")
async def serve_lesson_page(lesson_id: int):
    """
    Serve the lesson page HTML
    
    Args:
        lesson_id: Lesson ID from curriculum table
    
    Returns:
        HTML page with video, AI content, transcript, chat
    """
    return FileResponse("static/lesson_page.html")


@app.get("/api/lesson/{lesson_id}")
async def get_lesson_data(lesson_id: int) -> Dict[str, Any]:
    """
    Get complete lesson data including progress and navigation
    
    Args:
        lesson_id: Lesson ID from curriculum table
    
    Returns:
        {
          "lesson": {
            "lesson_id": 4,
            "lesson_title": "Introduction to Cognitive Functions",
            "lesson_number": 1,
            "season_number": "1",
            "season_name": "Jungian Cognitive Functions",
            "module_number": 2,
            "module_name": "Building Foundation",
            "youtube_url": "https://youtube.com/watch?v=...",
            "has_video": true,
            "transcript_id": "season01_01",
            "duration": "15:22",
            "order_index": 4
          },
          "progress": {
            "completed": false,
            "last_accessed": "2025-11-14T10:30:00"
          },
          "navigation": {
            "prev_lesson_id": 3,
            "next_lesson_id": 5,
            "has_prev": true,
            "has_next": true
          },
          "season_lessons": [
            {"lesson_id": 4, "lesson_number": 1, "lesson_title": "...", "completed": false},
            ...
          ]
        }
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get lesson data
        cursor.execute("""
            SELECT 
                c.lesson_id,
                c.lesson_title,
                c.lesson_number,
                c.season_number,
                c.season_name,
                c.module_number,
                c.module_name,
                c.youtube_url,
                c.has_video,
                c.transcript_id,
                c.duration,
                c.order_index,
                c.description
            FROM curriculum c
            WHERE c.lesson_id = %s
        """, (lesson_id,))
        
        lesson_row = cursor.fetchone()
        
        if not lesson_row:
            raise HTTPException(status_code=404, detail=f"Lesson {lesson_id} not found")
        
        lesson = {
            "lesson_id": int(lesson_row[0]),
            "lesson_title": str(lesson_row[1]),
            "lesson_number": int(lesson_row[2]),
            "season_number": str(lesson_row[3]),
            "season_name": str(lesson_row[4]),
            "module_number": int(lesson_row[5]),
            "module_name": str(lesson_row[6]),
            "youtube_url": str(lesson_row[7]) if lesson_row[7] else None,
            "has_video": bool(lesson_row[8]),
            "transcript_id": str(lesson_row[9]),
            "duration": str(lesson_row[10]) if lesson_row[10] else None,
            "order_index": int(lesson_row[11]),
            "description": str(lesson_row[12]) if lesson_row[12] else None
        }
        
        current_order = lesson["order_index"]
        season_number = lesson["season_number"]
        
        # Get or create progress
        cursor.execute("""
            SELECT completed, last_accessed
            FROM progress
            WHERE lesson_id = %s
        """, (lesson_id,))
        
        progress_row = cursor.fetchone()
        
        if progress_row:
            progress = {
                "completed": bool(progress_row[0]),
                "last_accessed": progress_row[1].isoformat() if progress_row[1] else None
            }
        else:
            # Create progress entry for this lesson
            cursor.execute("""
                INSERT INTO progress (lesson_id, completed, last_accessed)
                VALUES (%s, FALSE, CURRENT_TIMESTAMP)
            """, (lesson_id,))
            conn.commit()
            
            progress = {
                "completed": False,
                "last_accessed": None
            }
        
        # Update last_accessed
        cursor.execute("""
            UPDATE progress
            SET last_accessed = CURRENT_TIMESTAMP
            WHERE lesson_id = %s
        """, (lesson_id,))
        conn.commit()
        
        # Get previous lesson (same season only)
        cursor.execute("""
            SELECT lesson_id, lesson_title
            FROM curriculum
            WHERE season_number = %s
              AND order_index < %s
            ORDER BY order_index DESC
            LIMIT 1
        """, (season_number, current_order))
        
        prev_row = cursor.fetchone()
        prev_lesson_id = int(prev_row[0]) if prev_row else None
        
        # Get next lesson (same season only)
        cursor.execute("""
            SELECT lesson_id, lesson_title
            FROM curriculum
            WHERE season_number = %s
              AND order_index > %s
            ORDER BY order_index ASC
            LIMIT 1
        """, (season_number, current_order))
        
        next_row = cursor.fetchone()
        next_lesson_id = int(next_row[0]) if next_row else None
        
        navigation = {
            "prev_lesson_id": prev_lesson_id,
            "next_lesson_id": next_lesson_id,
            "has_prev": prev_lesson_id is not None,
            "has_next": next_lesson_id is not None
        }
        
        # Get all lessons in this season (for sidebar)
        cursor.execute("""
            SELECT 
                c.lesson_id,
                c.lesson_number,
                c.lesson_title,
                c.duration,
                p.completed
            FROM curriculum c
            LEFT JOIN progress p ON c.lesson_id = p.lesson_id
            WHERE c.season_number = %s
            ORDER BY c.order_index ASC
        """, (season_number,))
        
        season_lessons = []
        for row in cursor.fetchall():
            season_lessons.append({
                "lesson_id": int(row[0]),
                "lesson_number": int(row[1]),
                "lesson_title": str(row[2]),
                "duration": str(row[3]) if row[3] else None,
                "completed": bool(row[4]) if row[4] is not None else False
            })
        
        return {
            "lesson": lesson,
            "progress": progress,
            "navigation": navigation,
            "season_lessons": season_lessons
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting lesson data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.get("/api/lesson/{lesson_id}/chat")
async def get_lesson_chat(lesson_id: int) -> Dict[str, Any]:
    """
    Get chat history for a lesson
    
    Returns:
        {
          "messages": [
            {"role": "user", "content": "...", "timestamp": "..."},
            {"role": "assistant", "content": "...", "timestamp": "..."}
          ]
        }
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT messages
            FROM lesson_chats
            WHERE lesson_id = %s
        """, (lesson_id,))
        
        row = cursor.fetchone()
        
        if row and row[0]:
            messages = row[0]  # Already a list from JSONB
        else:
            messages = []
        
        return {"messages": messages}
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.post("/api/lesson/{lesson_id}/chat")
async def save_lesson_chat(lesson_id: int, message: Dict[str, str]):
    """
    Save a chat message for a lesson
    
    Args:
        message: {"role": "user"|"assistant", "content": "...", "timestamp": "..."}
    
    Returns:
        {"success": true}
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if chat history exists
        cursor.execute("""
            SELECT lesson_id FROM lesson_chats WHERE lesson_id = %s
        """, (lesson_id,))
        
        exists = cursor.fetchone()
        
        if exists:
            # Append to existing messages
            cursor.execute("""
                UPDATE lesson_chats
                SET 
                    messages = messages || %s::jsonb,
                    updated_at = CURRENT_TIMESTAMP
                WHERE lesson_id = %s
            """, (json.dumps([message]), lesson_id))
        else:
            # Create new chat history
            cursor.execute("""
                INSERT INTO lesson_chats (lesson_id, messages, created_at, updated_at)
                VALUES (%s, %s::jsonb, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (lesson_id, json.dumps([message])))
        
        conn.commit()
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error saving chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.post("/api/lesson/{lesson_id}/complete")
async def mark_lesson_complete(lesson_id: int):
    """
    Mark a lesson as complete
    
    Returns:
        {"success": true, "completed": true}
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Update or insert progress
        cursor.execute("""
            INSERT INTO progress (lesson_id, completed, last_accessed)
            VALUES (%s, TRUE, CURRENT_TIMESTAMP)
            ON CONFLICT (lesson_id)
            DO UPDATE SET 
                completed = TRUE,
                last_accessed = CURRENT_TIMESTAMP
        """, (lesson_id,))
        
        conn.commit()
        
        return {"success": True, "completed": True}
        
    except Exception as e:
        logger.error(f"Error marking lesson complete: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ==============================================================================
# END PHASE 7.3 ROUTES
# ==============================================================================
```

**Bug Checks:**
- ✅ Proper type conversion (int(), str(), bool())
- ✅ NULL handling for optional fields
- ✅ 404 if lesson not found
- ✅ Auto-create progress entry if missing
- ✅ Update last_accessed on every visit
- ✅ JSONB array concatenation for chat messages
- ✅ ON CONFLICT for mark complete (upsert)
- ✅ Resource cleanup (try/finally)
- ✅ SQL injection prevention (parameterized queries)

**Verification:**
```bash
# Test lesson data
curl http://localhost:5000/api/lesson/4 | jq '.'

# Test chat history (empty initially)
curl http://localhost:5000/api/lesson/4/chat | jq '.'

# Test mark complete
curl -X POST http://localhost:5000/api/lesson/4/complete | jq '.'
```

---

## 🎨 STEP 3: FRONTEND - HTML

### 3.1 Create static/lesson_page.html

**File:** `static/lesson_page.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Lesson - CS Joseph University</title>
    <link rel="stylesheet" href="/static/lesson_page.css">
</head>
<body data-theme="dark">
    <!-- Mobile Hamburger -->
    <button class="mobile-menu-toggle" id="mobileMenuToggle" aria-label="Toggle menu">
        <span class="hamburger-icon">☰</span>
    </button>

    <!-- Sidebar Overlay (Mobile) -->
    <div class="sidebar-overlay" id="sidebarOverlay"></div>

    <!-- Main Container -->
    <div class="lesson-container">
        
        <!-- Mini Sidebar -->
        <aside class="lesson-sidebar" id="lessonSidebar">
            <div class="sidebar-header">
                <a href="javascript:history.back()" class="back-link">
                    <span class="back-icon">←</span>
                    <span class="back-text">Back to Season</span>
                </a>
                
                <button id="themeToggle" class="theme-toggle-small" aria-label="Toggle theme">
                    <span class="theme-icon">🌙</span>
                </button>
            </div>

            <div class="sidebar-content" id="sidebarContent">
                <!-- Season lessons will be loaded here -->
                <div class="loading-spinner"></div>
            </div>
        </aside>

        <!-- Lesson Content -->
        <main class="lesson-main">
            <!-- Breadcrumb -->
            <nav class="breadcrumb" id="breadcrumb">
                <a href="/" class="breadcrumb-link">Dashboard</a>
                <span class="breadcrumb-separator">›</span>
                <span id="breadcrumbModule">...</span>
                <span class="breadcrumb-separator">›</span>
                <span id="breadcrumbSeason">...</span>
            </nav>

            <!-- Lesson Header -->
            <header class="lesson-header" id="lessonHeader">
                <div class="lesson-meta-small" id="lessonMetaSmall">Loading...</div>
                <h1 class="lesson-title" id="lessonTitle">Loading lesson...</h1>
            </header>

            <!-- Video Section -->
            <section class="video-section" id="videoSection">
                <!-- Video or Skool message will be inserted here -->
            </section>

            <!-- AI-Generated Lesson Content -->
            <section class="lesson-content-section">
                <h2 class="section-title">📝 Lesson Summary</h2>
                <div class="lesson-content" id="lessonContent">
                    <div class="loading-state">
                        <div class="spinner"></div>
                        <p>Generating lesson content...</p>
                    </div>
                </div>
                
                <button class="mark-complete-btn" id="markCompleteBtn" style="display: none;">
                    <span class="btn-icon">✓</span>
                    <span class="btn-text">Mark as Complete</span>
                </button>
            </section>

            <!-- Transcript Section -->
            <section class="transcript-section">
                <button class="transcript-toggle" id="transcriptToggle" disabled>
                    <span class="toggle-icon">📄</span>
                    <span class="toggle-text">Show Transcript</span>
                    <span class="toggle-arrow">▼</span>
                </button>
                
                <div class="transcript-content" id="transcriptContent" style="display: none;">
                    <div class="transcript-text" id="transcriptText">
                        <!-- Transcript will be loaded here -->
                    </div>
                </div>
            </section>

            <!-- Navigation -->
            <nav class="lesson-navigation">
                <button class="nav-btn prev-btn" id="prevBtn" disabled>
                    <span class="nav-icon">◀</span>
                    <span class="nav-text">Previous Lesson</span>
                </button>
                
                <button class="nav-btn next-btn" id="nextBtn" disabled>
                    <span class="nav-text">Next Lesson</span>
                    <span class="nav-icon">▶</span>
                </button>
            </nav>
        </main>

        <!-- AI Tutor Chat -->
        <aside class="chat-panel">
            <div class="chat-header">
                <h2 class="chat-title">💬 AI Tutor</h2>
                <p class="chat-subtitle">Ask anything about this lesson</p>
            </div>

            <div class="chat-messages" id="chatMessages">
                <!-- Chat messages will be loaded here -->
            </div>

            <div class="chat-input-container">
                <textarea 
                    id="chatInput"
                    class="chat-input"
                    placeholder="Ask a question about this lesson..."
                    rows="2"
                ></textarea>
                <button id="sendBtn" class="send-btn">
                    <span class="send-icon">▶</span>
                </button>
            </div>
        </aside>

    </div>

    <script src="/static/lesson_page.js"></script>
</body>
</html>
```

**Bug Checks:**
- ✅ All IDs unique
- ✅ Semantic HTML
- ✅ ARIA labels for accessibility
- ✅ Mobile meta viewport (no user scaling)
- ✅ data-theme for CSS theming
- ✅ history.back() for back navigation

---

## ✅ PART 1 VERIFICATION

Before proceeding to Part 2 (CSS), verify:

### Database ✅
```sql
-- Table exists
\d lesson_chats

-- Indexes exist
\di lesson_chats*

-- Test insert/select
INSERT INTO lesson_chats (lesson_id, messages)
VALUES (4, '[{"role":"user","content":"test"}]'::jsonb);

SELECT * FROM lesson_chats WHERE lesson_id = 4;

-- Cleanup
DELETE FROM lesson_chats WHERE lesson_id = 4;
```

### Backend ✅
```bash
# All 4 routes respond
curl http://localhost:5000/api/lesson/4
curl http://localhost:5000/api/lesson/4/chat
curl -X POST http://localhost:5000/api/lesson/4/complete
curl -X POST http://localhost:5000/api/lesson/4/chat \
  -H "Content-Type: application/json" \
  -d '{"role":"user","content":"test"}'
```

### HTML ✅
- [ ] File created at `static/lesson_page.html`
- [ ] Can access at `http://localhost:5000/lesson/4`
- [ ] Page loads (even if unstyled)
- [ ] No 404 errors
- [ ] HTML structure intact

---

## 🎯 NEXT STEPS

Once Part 1 is verified and working:

1. **Part 2:** Apply CSS styling (dark/light theme, responsive layout)
2. **Part 3:** Add JavaScript functionality (all interactive features)

**DO NOT proceed to Part 2 until user confirms Part 1 is working!**

---

**End of Part 1**
