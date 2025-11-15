-- Manual Pinecone Document Mappings for Season 1 (Foundation)
-- Based on actual video titles from document_report.csv

-- SEASON 1: JUNGIAN COGNITIVE FUNCTIONS (16 lessons)

-- Lesson 1: Introduction to Cognitive Functions
UPDATE curriculum SET document_id = '48634aad-f696-41c1-95e8-c6729f8c1524' 
WHERE lesson_id = 4;
-- [1] Cognitive Functions - How They Work - Foundation

-- Lesson 2: Parent vs Child Functions (no exact match, using optimistic/pessimistic)
UPDATE curriculum SET document_id = 'f8f82fe0-8e1c-448a-a4c7-988ca9256b5a' 
WHERE lesson_id = 5;
-- [1] Cognitive Functions - Optimistic vs Pessimistic - Foundation

-- Lesson 3: Hero Function Deep Dive (no individual function video, use intro)
UPDATE curriculum SET document_id = '7c27e2e7-ad22-4c29-a25b-c511cbde51dd' 
WHERE lesson_id = 6;
-- [1] Jungian Personality Types - Introduction - Foundation

-- Lesson 4-13: Individual Functions
-- Ti (Lesson 4: Child Function)
UPDATE curriculum SET document_id = '84a8ebbb-e983-4dbd-924c-36e1764d790f' 
WHERE lesson_id = 7;
-- [1] Introverted Thinking Ti - Individual Function - Foundation

-- Te (Lesson 5: Parent Function)
UPDATE curriculum SET document_id = '2776f175-6abe-48b9-81ba-0c046015394d' 
WHERE lesson_id = 8;
-- [1] Extraverted Thinking Te - Individual Function - Foundation

-- Fi (Lesson 6: Inferior Function)
UPDATE curriculum SET document_id = 'f7fac420-1906-449c-a42b-96408c20a80f' 
WHERE lesson_id = 9;
-- [1] Introverted Feeling Fi - Individual Function - Foundation

-- Fe (Lesson 7: Nemesis Function)
UPDATE curriculum SET document_id = '823fbd4a-274a-4db3-b665-c0b0b12243f2' 
WHERE lesson_id = 10;
-- [1] Extraverted Feeling Fe - Individual Function - Foundation

-- Si (Lesson 8: Critic Function)
UPDATE curriculum SET document_id = 'be4ab356-f3b8-49ac-b460-ddf4fb325e22' 
WHERE lesson_id = 11;
-- [1] Introverted Sensing Si - Individual Function - Foundation

-- Se (Lesson 9: Trickster Function)
UPDATE curriculum SET document_id = 'a2297710-6f69-4fa6-8562-4199da8b506d' 
WHERE lesson_id = 12;
-- [1] Extraverted Sensing Se - Individual Function - Foundation

-- Ni (Lesson 10: Demon Function)
UPDATE curriculum SET document_id = 'ef51f8b4-2a6c-49eb-bf63-e616da6db364' 
WHERE lesson_id = 13;
-- [1] Introverted Intuition Ni - Individual Function - Foundation

-- Ne (Lesson 14: Ti vs Te)
UPDATE curriculum SET document_id = '1d9018cd-aa2e-4b71-bf75-64282b852850' 
WHERE lesson_id = 14;
-- [1] Extraverted Intuition Ne - Individual Function - Foundation

-- Lesson 15: Fi vs Fe (use Fe video)
UPDATE curriculum SET document_id = '823fbd4a-274a-4db3-b665-c0b0b12243f2' 
WHERE lesson_id = 15;
-- [1] Extraverted Feeling Fe - Individual Function - Foundation

-- Lesson 16: Si vs Se (use Si video)
UPDATE curriculum SET document_id = 'be4ab356-f3b8-49ac-b460-ddf4fb325e22' 
WHERE lesson_id = 16;
-- [1] Introverted Sensing Si - Individual Function - Foundation

-- Lesson 17: Ni vs Ne (use Ni video)
UPDATE curriculum SET document_id = 'ef51f8b4-2a6c-49eb-bf63-e616da6db364' 
WHERE lesson_id = 17;
-- [1] Introverted Intuition Ni - Individual Function - Foundation

-- Lesson 18: Function Axes
UPDATE curriculum SET document_id = 'dacf3c93-b36a-4a22-974d-3e30b44616eb' 
WHERE lesson_id = 18;
-- [1] Cognitive Axis - Explanation - Foundation

-- Lesson 19: Cognitive Function Stack Summary
UPDATE curriculum SET document_id = '28a1d0b9-3b98-4227-887a-3b75718dda3e' 
WHERE lesson_id = 19;
-- [1] Four Sides of the Mind - Introduction - Foundation

-- SEASON 0: ORIENTATION (No Pinecone documents available)
-- These will return graceful fallback message

-- SEASON 16: COGNITIVE ATTITUDES
-- Already mapped by auto-matcher (seemed accurate)

-- SEASON 2: HOW TO TYPE YOURSELF (need to check CSV for Season 2 docs)
UPDATE curriculum SET document_id = 'a33ab235-7052-48c0-bc76-1acf6ad4de28'
WHERE lesson_id = 28;
-- [2] Type Grid - How To Type Anyone - Practical Guide
