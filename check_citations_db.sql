-- Check if citations are being saved to database
-- Run this on Replit: psql $DATABASE_URL < check_citations_db.sql

SELECT 
    id,
    conversation_id,
    role,
    LEFT(content, 50) as content_preview,
    follow_up_question IS NOT NULL as has_followup,
    citations IS NOT NULL as has_citations,
    citations as citations_data
FROM messages 
WHERE conversation_id = 102  -- Your current conversation ID
ORDER BY created_at DESC 
LIMIT 5;

-- This will show:
-- has_followup: Should be 'true' for recent messages
-- has_citations: Should be 'true' for recent messages (if working)
-- citations_data: Should show JSON data (if saved)

