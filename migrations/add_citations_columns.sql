-- Migration: Add citations and follow_up_question columns to messages table
-- Date: 2025-12-01
-- Purpose: Enable persistence of citations and follow-up questions for last N messages

-- Add columns if they don't exist
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS follow_up_question TEXT,
ADD COLUMN IF NOT EXISTS citations JSONB;

-- Create index for faster queries on recent messages with citations
CREATE INDEX IF NOT EXISTS idx_messages_with_citations 
ON messages(conversation_id, created_at DESC) 
WHERE citations IS NOT NULL;

-- Comment for documentation
COMMENT ON COLUMN messages.citations IS 'RAG citations data (sources, confidence) saved for last 6 messages only';
COMMENT ON COLUMN messages.follow_up_question IS 'Suggested follow-up question for user, saved for last 6 messages only';








