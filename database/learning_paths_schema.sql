-- ============================================================================
-- INNERVERSE LEARNING PATHS - POSTGRESQL SCHEMA
-- Creates: courses, lessons, user_progress, course_prerequisites tables
-- Safe to run multiple times (uses IF NOT EXISTS)
-- ============================================================================

-- TABLE 1: COURSES (Learning Tracks)
-- ============================================================================
CREATE TABLE IF NOT EXISTS courses (
    -- Identity
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL CHECK(category IN ('foundations', 'your_type', 'relationships', 'advanced')),
    description TEXT,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Metadata
    estimated_hours REAL DEFAULT 0,
    auto_generated BOOLEAN DEFAULT TRUE,
    generation_prompt TEXT,
    source_type VARCHAR(50),  -- 'chat', 'graph', 'atlas', 'manual'
    source_ids JSONB,  -- JSON array: ["doc_id_1", "doc_id_2"]
    
    -- Organization
    status VARCHAR(20) DEFAULT 'active' CHECK(status IN ('active', 'archived', 'deleted')),
    tags JSONB,  -- JSON array: ["enfp", "shadow", "relationships"]
    
    -- Denormalized stats (updated via triggers or manually)
    lesson_count INTEGER DEFAULT 0,
    total_concepts INTEGER DEFAULT 0,
    
    -- User preferences
    custom_order INTEGER DEFAULT 0,
    notes TEXT
);

-- TABLE 2: LESSONS (Individual learning units within a track)
-- ============================================================================
CREATE TABLE IF NOT EXISTS lessons (
    -- Identity
    id VARCHAR(36) PRIMARY KEY,
    course_id VARCHAR(36) NOT NULL,
    
    -- Content
    title VARCHAR(255) NOT NULL,
    description TEXT,
    order_index INTEGER NOT NULL,  -- 1-based ordering within course
    
    -- Concept links (references knowledge graph)
    concept_ids JSONB NOT NULL,  -- JSON array: ["concept_uuid_1", "concept_uuid_2"]
    prerequisite_lesson_ids JSONB,  -- JSON array: ["lesson_uuid_1"] or NULL
    
    -- Metadata
    estimated_minutes INTEGER DEFAULT 30,
    difficulty VARCHAR(50) CHECK(difficulty IN ('foundational', 'intermediate', 'advanced')) DEFAULT 'foundational',
    
    -- Source material
    video_references JSONB,  -- JSON: [{"video_id": "S02E05", "timestamp": "12:30", "youtube_url": "https://...", "context": "Discusses Fi"}]
    document_references JSONB,  -- JSON array: ["doc_uuid_1", "doc_uuid_2"]
    
    -- Teaching notes
    learning_objectives TEXT,
    key_takeaways TEXT,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Foreign key
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

-- TABLE 3: USER_PROGRESS (Tracks learning progress per user per course)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_progress (
    -- Identity
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(100) DEFAULT 'jeralyn',  -- Future-proof for multi-user
    course_id VARCHAR(36) NOT NULL,
    
    -- Progress tracking
    current_lesson_id VARCHAR(36),  -- CRITICAL: Only ONE active lesson system-wide
    completed_lesson_ids JSONB,  -- JSON array: ["lesson_uuid_1", "lesson_uuid_2"]
    
    -- Timestamps
    started_at TIMESTAMP,
    last_accessed TIMESTAMP,
    completed_at TIMESTAMP,  -- NULL if course not finished
    
    -- Engagement
    total_time_minutes INTEGER DEFAULT 0,
    lesson_completion_dates JSONB,  -- JSON object: {"lesson_uuid_1": "2025-01-15T10:30:00Z"}
    
    -- Learning notes
    notes JSONB,  -- JSON object: {"lesson_uuid_1": "My notes here", "lesson_uuid_2": "More notes"}
    flagged_for_review JSONB,  -- JSON array: ["lesson_uuid_1", "lesson_uuid_3"]
    ai_validation_status JSONB,  -- JSON object: {"lesson_uuid_1": "validated", "lesson_uuid_2": "pending"}
    
    -- Foreign key
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    
    -- Unique constraint
    UNIQUE(user_id, course_id)
);

-- TABLE 4: COURSE_PREREQUISITES (Defines prerequisite relationships between tracks)
-- ============================================================================
CREATE TABLE IF NOT EXISTS course_prerequisites (
    -- Identity
    id VARCHAR(36) PRIMARY KEY,
    course_id VARCHAR(36) NOT NULL,
    prerequisite_course_id VARCHAR(36) NOT NULL,
    required BOOLEAN DEFAULT FALSE,  -- false = recommended, true = required
    
    -- Foreign keys
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY (prerequisite_course_id) REFERENCES courses(id) ON DELETE CASCADE,
    
    -- Unique constraint (can't have duplicate prerequisites)
    UNIQUE(course_id, prerequisite_course_id),
    
    -- Self-reference check (course can't be its own prerequisite)
    CHECK(course_id != prerequisite_course_id)
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Courses indexes
CREATE INDEX IF NOT EXISTS idx_courses_category ON courses(category);
CREATE INDEX IF NOT EXISTS idx_courses_status ON courses(status);
CREATE INDEX IF NOT EXISTS idx_courses_updated ON courses(updated_at DESC);

-- Lessons indexes
CREATE INDEX IF NOT EXISTS idx_lessons_course ON lessons(course_id);
CREATE INDEX IF NOT EXISTS idx_lessons_order ON lessons(course_id, order_index);

-- User progress indexes
CREATE INDEX IF NOT EXISTS idx_progress_user ON user_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_progress_course ON user_progress(course_id);
CREATE INDEX IF NOT EXISTS idx_progress_active ON user_progress(current_lesson_id) WHERE current_lesson_id IS NOT NULL;

-- Prerequisites indexes
CREATE INDEX IF NOT EXISTS idx_prereq_course ON course_prerequisites(course_id);
CREATE INDEX IF NOT EXISTS idx_prereq_prerequisite ON course_prerequisites(prerequisite_course_id);

-- ============================================================================
-- TRIGGERS FOR DATA INTEGRITY
-- ============================================================================

-- Update courses.updated_at on any course update
CREATE OR REPLACE FUNCTION update_course_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_course_timestamp ON courses;
CREATE TRIGGER trigger_update_course_timestamp
BEFORE UPDATE ON courses
FOR EACH ROW
EXECUTE FUNCTION update_course_timestamp();

-- Update courses.lesson_count when lessons added/removed
CREATE OR REPLACE FUNCTION update_lesson_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE courses 
        SET lesson_count = (SELECT COUNT(*) FROM lessons WHERE course_id = NEW.course_id)
        WHERE id = NEW.course_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE courses 
        SET lesson_count = (SELECT COUNT(*) FROM lessons WHERE course_id = OLD.course_id)
        WHERE id = OLD.course_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_lesson_count_insert ON lessons;
CREATE TRIGGER trigger_update_lesson_count_insert
AFTER INSERT ON lessons
FOR EACH ROW
EXECUTE FUNCTION update_lesson_count();

DROP TRIGGER IF EXISTS trigger_update_lesson_count_delete ON lessons;
CREATE TRIGGER trigger_update_lesson_count_delete
AFTER DELETE ON lessons
FOR EACH ROW
EXECUTE FUNCTION update_lesson_count();

-- ============================================================================
-- SCHEMA VERSION TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_versions (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT NOW(),
    description TEXT
);

INSERT INTO schema_versions (version, description) 
VALUES (1, 'Initial Learning Paths schema - courses, lessons, user_progress, course_prerequisites')
ON CONFLICT (version) DO NOTHING;
