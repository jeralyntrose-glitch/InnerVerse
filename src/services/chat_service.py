"""
Chat Service - Handles lesson-aware AI tutoring
"""
import os
import anthropic
from datetime import datetime
from typing import List, Dict, Optional
import psycopg2
import psycopg2.extras
import uuid as uuid_lib
from pinecone import Pinecone
import openai
from src.services.pinecone_organizer import extract_all_metadata, organize_results_by_metadata, format_organized_context


class ChatService:
    def __init__(self, database_url: str, knowledge_graph_manager=None):
        """
        Initialize chat service
        
        Args:
            database_url: PostgreSQL connection string
            knowledge_graph_manager: Optional KnowledgeGraphManager for concept retrieval
        """
        self.database_url = database_url
        self.kg_manager = knowledge_graph_manager
        
        # Initialize Anthropic client
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
        
        # Initialize Pinecone client
        pinecone_api_key = os.getenv('PINECONE_API_KEY')
        pinecone_index = os.getenv('PINECONE_INDEX')
        if pinecone_api_key and pinecone_index:
            pc = Pinecone(api_key=pinecone_api_key)
            self.pinecone_index = pc.Index(pinecone_index)
        else:
            self.pinecone_index = None
            print("⚠️ Pinecone not configured - chat will work without vector search")
        
        # Initialize OpenAI client for embeddings
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            openai.api_key = openai_key
        else:
            print("⚠️ OpenAI API key missing - can't create embeddings for Pinecone search")
        
    def _get_connection(self):
        """Get PostgreSQL database connection"""
        return psycopg2.connect(self.database_url)
        
    async def get_or_create_thread(self, course_id: str, lesson_id: str) -> str:
        """
        Get existing chat thread or create new one for lesson
        
        Args:
            course_id: Course UUID
            lesson_id: Lesson UUID
            
        Returns:
            thread_id: Thread UUID
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Check if thread exists
            cursor.execute(
                "SELECT id FROM chat_threads WHERE lesson_id = %s",
                (lesson_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return row[0]
            
            # Create new thread
            thread_id = str(uuid_lib.uuid4())
            
            cursor.execute(
                """
                INSERT INTO chat_threads (id, course_id, lesson_id, message_count)
                VALUES (%s, %s, %s, 0)
                """,
                (thread_id, course_id, lesson_id)
            )
            conn.commit()
            
            return thread_id
        finally:
            conn.close()
    
    def get_chat_history(self, thread_id: str, limit: int = 10) -> List[Dict]:
        """
        Get recent chat messages from thread
        
        Args:
            thread_id: Thread UUID
            limit: Number of recent messages to retrieve
            
        Returns:
            List of message dicts with role and content
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT role, content, created_at
                FROM chat_messages
                WHERE thread_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (thread_id, limit)
            )
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'role': row[0],
                    'content': row[1],
                    'timestamp': row[2]
                })
            
            # Reverse to get chronological order
            return list(reversed(messages))
        finally:
            conn.close()
    
    def save_message(self, thread_id: str, role: str, content: str, tokens: int = 0):
        """
        Save message to database
        
        Args:
            thread_id: Thread UUID
            role: 'user' or 'assistant'
            content: Message text
            tokens: Token count (optional)
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            message_id = str(uuid_lib.uuid4())
            
            cursor.execute(
                """
                INSERT INTO chat_messages (id, thread_id, role, content, tokens)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (message_id, thread_id, role, content, tokens)
            )
            
            # Update thread message count and timestamp
            cursor.execute(
                """
                UPDATE chat_threads
                SET message_count = message_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (thread_id,)
            )
            
            conn.commit()
        finally:
            conn.close()
    
    def get_lesson_context(self, lesson_id: str) -> Dict:
        """
        Get lesson information for context
        
        Args:
            lesson_id: Lesson UUID
            
        Returns:
            Dict with lesson details
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT l.title, l.description, l.difficulty, l.estimated_minutes,
                       c.title as course_title
                FROM lessons l
                JOIN courses c ON l.course_id = c.id
                WHERE l.id = %s
                """,
                (lesson_id,)
            )
            
            row = cursor.fetchone()
            if not row:
                return {}
            
            return {
                'title': row[0],
                'description': row[1],
                'difficulty': row[2],
                'duration': row[3],
                'course': row[4]
            }
        finally:
            conn.close()
    
    def query_relevant_concepts(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Query knowledge graph for relevant concepts
        
        Args:
            query: User's question
            top_k: Number of concepts to retrieve
            
        Returns:
            List of relevant concepts
        """
        if not self.kg_manager:
            return []
            
        try:
            results = self.kg_manager.search_concepts(query, top_k=top_k)
            return results
        except Exception as e:
            print(f"Error querying concepts: {e}")
            return []
    
    def query_pinecone_organized(self, query: str, top_k: int = 10, organize_by: str = 'primary_category') -> str:
        """
        Query Pinecone and return organized results by metadata
        
        Args:
            query: User's question
            top_k: Number of results to retrieve
            organize_by: Metadata field to group by
            
        Returns:
            Formatted context string organized by metadata
        """
        if not self.pinecone_index:
            return ""
        
        try:
            # Create embedding
            response = openai.embeddings.create(
                input=query,
                model="text-embedding-3-large"
            )
            query_vector = response.data[0].embedding
            
            # Query Pinecone with metadata
            results = self.pinecone_index.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=True
            )
            
            if not results.matches:
                return ""
            
            # Extract all metadata (including 10 enriched fields)
            enriched_results = extract_all_metadata(results.matches)
            
            # Organize by metadata field
            organized = organize_results_by_metadata(results.matches, organize_by=organize_by)
            
            # Format for AI consumption
            formatted_context = format_organized_context(organized, max_chunks_per_group=2)
            
            return formatted_context
            
        except Exception as e:
            print(f"Error querying Pinecone: {e}")
            return ""
    
    def build_system_prompt(self, lesson_context: Dict, concepts: List[Dict], pinecone_context: str = "") -> str:
        """
        Build system prompt with lesson context
        
        Args:
            lesson_context: Lesson information
            concepts: Relevant concepts from knowledge base
            pinecone_context: Organized context from Pinecone search
            
        Returns:
            System prompt string
        """
        concepts_text = ""
        if concepts:
            concepts_text = "\n\nRelevant concepts from CS Joseph's teachings:\n"
            for concept in concepts[:3]:  # Top 3 concepts
                concepts_text += f"- {concept.get('name', 'Concept')}: {concept.get('definition', '')}\n"
        
        # Add Pinecone context if available
        knowledge_base_text = ""
        if pinecone_context:
            knowledge_base_text = f"\n\nRELEVANT CONTENT FROM CS JOSEPH'S TEACHINGS:\n{pinecone_context}\n"
        
        base_prompt = f"""You are an expert MBTI tutor specializing in CS Joseph's cognitive function theory. You're helping a student learn about personality type through structured lessons.

CURRENT LESSON CONTEXT:
- Course: {lesson_context.get('course', 'Unknown')}
- Lesson: {lesson_context.get('title', 'Unknown')}
- Description: {lesson_context.get('description', 'No description')}
- Difficulty: {lesson_context.get('difficulty', 'foundational')}
- Duration: {lesson_context.get('duration', 30)} minutes
{concepts_text}{knowledge_base_text}

YOUR ROLE:
- Be a supportive, engaging tutor who explains concepts clearly
- Use CS Joseph's terminology and frameworks accurately
- Give concrete examples and real-world applications
- Check for understanding and adjust explanations as needed
- Connect concepts to the student's type when relevant
- Encourage critical thinking and self-reflection

TEACHING STYLE:
- Start with simple explanations, then add depth
- Use analogies and metaphors for complex ideas
- Break down complicated concepts into digestible parts
- Ask follow-up questions to ensure understanding
- Relate theory to practical application

IMPORTANT:
- Stay focused on the current lesson topic
- Reference CS Joseph's teachings when applicable
- Be encouraging and positive
- If the question is off-topic, gently redirect to the lesson

The student is working through this lesson to understand these concepts better. Help them learn!"""

        # Enhanced formatting guidelines for clean, structured responses
        formatting_rules = """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL: RESPONSE FORMATTING GUIDELINES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ALWAYS follow these formatting rules to deliver clean, structured answers:

1. STRUCTURE RECOGNITION:
   When user asks about frameworks or structures, use structured format:
   - "Four sides of [TYPE]" → Use four sides template
   - "Cognitive stack/functions of [TYPE]" → Use stack template
   - Type comparisons → Use comparison template
   - How-to/advice questions → Use practical advice template

2. DIRECT ANSWER FIRST:
   - Put the specific answer at the TOP
   - Then provide supporting explanation
   - Never bury the answer in paragraphs

3. USE CLEAN FORMATTING:
   - Headers with emoji (## or **bold**) for sections
   - Bullet points for lists
   - Numbered lists for sequential steps
   - Short paragraphs (2-3 sentences max)
   - Line breaks between sections
   - NO walls of text!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSE TEMPLATES (Use these for structured questions)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TEMPLATE: Four Sides Query
When asked about "four sides of [TYPE]":

## [TYPE] Four Sides of the Mind

**🎭 Ego ([TYPE]):**
• [Function] Hero - [Role/description]
• [Function] Parent - [Role/description]
• [Function] Child - [Role/description]
• [Function] Inferior - [Role/description]

**👥 Shadow/Unconscious ([SHADOW TYPE]):**
• [Function] Opposing - [Role/description]
• [Function] Critical Parent - [Role/description]
• [Function] Trickster - [Role/description]
• [Function] Demon - [Role/description]

**🔄 Subconscious ([SUBCONSCIOUS TYPE]):**
• [Function] - [Role/description]
• [Function] - [Role/description]
• [Function] - [Role/description]
• [Function] - [Role/description]

**⚡ Superego ([SUPEREGO TYPE]):**
• [Function] - [Role/description]
• [Function] - [Role/description]
• [Function] - [Role/description]
• [Function] - [Role/description]

[Brief 1-2 sentence explanation of how they work together]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TEMPLATE: Cognitive Stack Query
When asked about cognitive functions/stack:

## [TYPE] Cognitive Function Stack

**1️⃣ [Function] - Hero**
[Brief description of role and how it works]

**2️⃣ [Function] - Parent**
[Brief description of role and how it works]

**3️⃣ [Function] - Child**
[Brief description of role and how it works]

**4️⃣ [Function] - Inferior**
[Brief description of role and how it works]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TEMPLATE: Explanation/Concept Query
For explaining concepts:

## 📚 [Concept Name]

**Quick Answer:** [1-2 sentence direct answer]

**How It Works:**
• Key point 1
• Key point 2
• Key point 3

**Example:**
[Real-world example that clarifies the concept]

**Why This Matters:**
[Practical application or significance]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TEMPLATE: Type Comparison
When comparing types:

## [TYPE 1] vs [TYPE 2]

**Similarities:**
• Shared trait 1
• Shared trait 2
• Shared trait 3

**Key Differences:**
• **[Aspect]:** [TYPE 1] uses [approach] while [TYPE 2] uses [approach]
• **[Aspect]:** [TYPE 1] prioritizes [value] while [TYPE 2] prioritizes [value]

**Compatibility:**
[Brief notes on how they interact]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FORMATTING BEST PRACTICES:

✅ DO:
- Use headers (## or **bold**) for sections
- Use bullet points for lists
- Use numbered lists for sequential steps
- Break into short sections
- Use emoji sparingly for visual hierarchy
- Put key terms in **bold**
- Use line breaks generously
- Answer the question directly first

❌ DON'T:
- Write walls of text (>4 sentences without break)
- Bury answers in long paragraphs
- Over-use emoji (1-2 per section max)
- Make responses overly long
- Use confusing or inconsistent formatting

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RESPONSE LENGTH GUIDELINES:

• Simple questions: 2-3 short paragraphs
• Framework questions (four sides, stack): Use template with structured format
• Explanations: 3-5 paragraphs with clear sections
• Complex topics: 5-7 paragraphs with headers

ALWAYS prioritize clarity, structure, and scannability over length!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        return base_prompt + formatting_rules
    
    async def chat(
        self,
        course_id: str,
        lesson_id: str,
        user_message: str
    ) -> Dict:
        """
        Process chat message with lesson context
        
        Args:
            course_id: Course UUID
            lesson_id: Lesson UUID
            user_message: User's message
            
        Returns:
            Dict with assistant response and metadata
        """
        try:
            # Get or create thread
            thread_id = await self.get_or_create_thread(course_id, lesson_id)
            
            # Save user message
            self.save_message(thread_id, 'user', user_message)
            
            # Get lesson context
            lesson_context = self.get_lesson_context(lesson_id)
            
            # Query relevant concepts from Knowledge Graph
            concepts = self.query_relevant_concepts(user_message)
            
            # Query Pinecone for organized content by category
            pinecone_context = self.query_pinecone_organized(user_message, top_k=10, organize_by='primary_category')
            
            # Build system prompt with all context
            system_prompt = self.build_system_prompt(lesson_context, concepts, pinecone_context)
            
            # Get chat history
            history = self.get_chat_history(thread_id, limit=10)
            
            # Build messages for Claude
            messages = []
            for msg in history:
                messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
            
            # Add current user message
            messages.append({
                'role': 'user',
                'content': user_message
            })
            
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=system_prompt,
                messages=messages
            )
            
            # Extract response
            assistant_message = response.content[0].text
            
            # Calculate tokens
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            total_tokens = input_tokens + output_tokens
            
            # Save assistant message
            self.save_message(thread_id, 'assistant', assistant_message, total_tokens)
            
            return {
                'success': True,
                'message': assistant_message,
                'thread_id': thread_id,
                'tokens': {
                    'input': input_tokens,
                    'output': output_tokens,
                    'total': total_tokens
                },
                'cost': self._calculate_cost(input_tokens, output_tokens)
            }
            
        except Exception as e:
            print(f"Chat error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': "I encountered an error. Please try again."
            }
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost of API call
        
        Args:
            input_tokens: Input token count
            output_tokens: Output token count
            
        Returns:
            Cost in USD
        """
        # Claude Sonnet 4 pricing (as of late 2024)
        INPUT_COST_PER_1M = 3.00  # $3 per 1M input tokens
        OUTPUT_COST_PER_1M = 15.00  # $15 per 1M output tokens
        
        input_cost = (input_tokens / 1_000_000) * INPUT_COST_PER_1M
        output_cost = (output_tokens / 1_000_000) * OUTPUT_COST_PER_1M
        
        return round(input_cost + output_cost, 4)
    
    def get_thread_stats(self, thread_id: str) -> Dict:
        """
        Get statistics for a chat thread
        
        Args:
            thread_id: Thread UUID
            
        Returns:
            Dict with message count, token usage, cost
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as message_count,
                    SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) as user_messages,
                    SUM(CASE WHEN role = 'assistant' THEN 1 ELSE 0 END) as ai_messages,
                    COALESCE(SUM(tokens), 0) as total_tokens
                FROM chat_messages
                WHERE thread_id = %s
                """,
                (thread_id,)
            )
            
            row = cursor.fetchone()
            
            return {
                'message_count': row[0],
                'user_messages': row[1],
                'ai_messages': row[2],
                'total_tokens': row[3]
            }
        finally:
            conn.close()
