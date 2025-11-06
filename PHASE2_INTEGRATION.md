# InnerVerse Learning Paths - Phase 2 Integration

## Overview
Phase 2 adds AI-powered course generation and automatic content assignment using Claude Sonnet 4.

## ✅ Implementation Complete

### Files Created
1. ✅ `src/services/course_generator.py` - AI curriculum generation (409 lines)
2. ✅ `src/services/content_assigner.py` - 3-tier confidence assignment (412 lines)
3. ✅ `src/services/knowledge_graph_manager.py` - Added required methods (get_concept, search_concepts)

### Files Modified
1. ✅ `src/services/course_manager.py` - Added helper methods (get_all_courses, get_course_with_lessons, get_all_courses_with_lessons)
2. ✅ `main.py` - Added dependency injection and 3 new API endpoints

## 🚀 New API Endpoints

### 1. POST /api/courses/generate
Generate a complete course curriculum from user goal using AI.

**Request:**
```json
{
  "user_goal": "Master ENFP shadow integration",
  "relevant_concept_ids": ["concept-1", "concept-2"],
  "max_lessons": 12,
  "target_category": "advanced"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Generated course 'ENFP Shadow Mastery' with 10 lessons",
  "course_id": "uuid-here",
  "course": { ... },
  "lesson_ids": ["uuid-1", "uuid-2", ...],
  "cost": 0.05
}
```

**Cost:** ~$0.03-0.08 per course generation

---

### 2. POST /api/courses/assign-content
Assign new document content to existing tracks using 3-tier confidence system.

**Request:**
```json
{
  "document_id": "doc-uuid-123",
  "extracted_concept_ids": ["concept-1", "concept-2", "concept-3"],
  "document_metadata": {
    "title": "ENFP Ne Hero Function",
    "video_id": "S02E05",
    "duration_minutes": 45
  },
  "auto_create_lesson": true
}
```

**Response (High Confidence - 90%+):**
```json
{
  "success": true,
  "message": "Content assigned to 'ENFP Mastery' (high confidence) - Lesson created: ENFP Ne Hero Function",
  "assignment": {
    "action": "add_to_existing",
    "course_id": "uuid",
    "confidence": 0.95,
    "confidence_tier": "high",
    "reasoning": "High confidence match (95% concept overlap). Auto-added.",
    "suggested_lesson": { ... },
    "cost": 0.0
  },
  "lesson_id": "lesson-uuid"
}
```

**Response (Medium Confidence - 70-89%):**
```json
{
  "success": true,
  "message": "Content assigned to 'ENFP Mastery' (medium confidence) - Lesson created: ...",
  "assignment": {
    "action": "add_to_existing",
    "course_id": "uuid",
    "confidence": 0.78,
    "confidence_tier": "medium",
    "reasoning": "Strong alignment with ENFP concepts. The Ne and Fi functions covered match 7 of 9 core concepts in this track.",
    "suggested_lesson": { ... },
    "cost": 0.02
  },
  "lesson_id": "lesson-uuid"
}
```

**Response (Low Confidence - <70%):**
```json
{
  "success": true,
  "message": "Recommend creating new track: 'Learning Path: Introverted Thinking'",
  "assignment": {
    "action": "create_new",
    "course_id": null,
    "confidence": 0.0,
    "confidence_tier": "low",
    "reasoning": "Low confidence match with existing tracks. Creating new track recommended. Best existing match was 'ENFP Mastery' at 45% overlap.",
    "suggested_course": { ... },
    "suggested_lesson": { ... },
    "cost": 0.0
  },
  "lesson_id": null
}
```

**Confidence Tiers:**
- **High (90%+):** Auto-add silently - NO API call ($0.00)
- **Medium (70-89%):** Auto-add with Claude reasoning (~$0.01-0.02)
- **Low (<70%):** Recommend new track - NO API call ($0.00)

---

### 3. GET /api/courses/generation-stats
Get AI generation statistics for current session.

**Response:**
```json
{
  "success": true,
  "data": {
    "generation_cost": 0.15,
    "assignment_cost": 0.08,
    "total_cost": 0.23
  }
}
```

---

## 🔧 Architecture

### Dependency Injection
```python
# In main.py

def get_course_generator():
    """Get CourseGenerator instance"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
    return CourseGenerator(
        anthropic_api_key=ANTHROPIC_API_KEY,
        knowledge_graph_manager=kg_manager
    )

def get_content_assigner():
    """Get ContentAssigner instance"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="Database not configured")
    return ContentAssigner(
        anthropic_api_key=ANTHROPIC_API_KEY,
        knowledge_graph_manager=kg_manager,
        course_manager=CourseManager(DATABASE_URL)
    )
```

### Integration Points

**CourseGenerator** requires:
- `KnowledgeGraphManager.get_concept(concept_id)` ✅ Implemented
- `KnowledgeGraphManager.search_concepts(query, top_k)` ✅ Implemented

**ContentAssigner** requires:
- `CourseManager.get_all_courses(include_archived)` ✅ Implemented
- `CourseManager.list_lessons(course_id)` ✅ Already exists
- `KnowledgeGraphManager.get_concept(concept_id)` ✅ Implemented

---

## 💰 Cost Management

### Per-Operation Costs
- **Course Generation:** ~$0.03-0.08 per course (Claude Sonnet 4 API call)
- **High Confidence Assignment:** $0.00 (no API call)
- **Medium Confidence Assignment:** ~$0.01-0.02 (short Claude reasoning call)
- **Low Confidence Assignment:** $0.00 (no API call)

### Cost Tracking
```python
from main import get_course_generator, get_content_assigner

# Get current session costs
generator = get_course_generator()
assigner = get_content_assigner()

print(f"Generation cost: ${generator.get_total_cost():.4f}")
print(f"Assignment cost: ${assigner.get_total_cost():.4f}")

# Reset cost tracking
generator.reset_cost_tracking()
assigner.reset_cost_tracking()
```

---

## 🧪 Testing

### Test 1: Generate Course
```bash
curl -X POST http://localhost:5000/api/courses/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_goal": "Master ENFP cognitive functions",
    "max_lessons": 10,
    "target_category": "your_type"
  }'
```

### Test 2: Assign Content (Manual - No Auto-Create)
```bash
curl -X POST http://localhost:5000/api/courses/assign-content \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "test-doc-123",
    "extracted_concept_ids": ["concept-1", "concept-2"],
    "document_metadata": {
      "title": "Understanding Ne Hero",
      "duration_minutes": 45
    },
    "auto_create_lesson": false
  }'
```

### Test 3: Get Generation Stats
```bash
curl http://localhost:5000/api/courses/generation-stats
```

---

## 🔮 Future Enhancements

### Phase 3 Ideas (Not Implemented)
- Frontend UI for course generation
- Visual course builder with drag & drop
- Prerequisite chain visualization
- Content recommendation engine
- Batch content assignment

---

## ⚙️ Environment Variables

Make sure these are set in Replit Secrets:

```bash
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DATABASE_URL=your_postgresql_connection_string  # Already configured
```

---

## 📊 System Health

### KnowledgeGraphManager Methods Added
```python
def get_concept(self, concept_id: str) -> Optional[Dict[str, Any]]:
    """Get a single concept by ID"""
    
def search_concepts(self, query: str, top_k: int = 30) -> List[Dict[str, Any]]:
    """Search concepts by semantic similarity"""
```

### CourseManager Helper Methods Added
```python
def get_all_courses(self, include_archived: bool = False) -> Dict[str, List[Dict[str, Any]]]:
    """Get all courses grouped by category"""

def get_course_with_lessons(self, course_id: str) -> Optional[Dict[str, Any]]:
    """Get course with all lessons embedded"""

def get_all_courses_with_lessons(self, include_archived: bool = False) -> List[Dict[str, Any]]:
    """Get all courses with lessons embedded"""
```

---

## 🎯 Phase 2 Summary

**Status:** ✅ **COMPLETE**

**What We Built:**
- 🤖 AI-powered course generation from user goals
- 🎯 Smart content assignment with 3-tier confidence
- 💰 Cost tracking for all AI operations
- 🔗 Full integration with Knowledge Graph
- 📊 3 new production-ready API endpoints

**Lines of Code:**
- `course_generator.py`: 409 lines
- `content_assigner.py`: 412 lines
- `knowledge_graph_manager.py`: +129 lines
- `course_manager.py`: +91 lines
- `main.py`: +208 lines

**Total:** ~1,249 new lines of production code

---

## 🚦 Next Steps

1. ✅ Test all 3 endpoints
2. ✅ Verify cost tracking works
3. ✅ Confirm Knowledge Graph integration
4. 📝 Document frontend integration patterns
5. 🎨 Consider Phase 3: Canvas UI

**Phase 2 is production-ready!** 🎉
