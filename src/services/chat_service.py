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
    
    def build_system_prompt(self, lesson_context: Dict, concepts: List[Dict]) -> str:
        """
        Build system prompt with lesson context
        
        Args:
            lesson_context: Lesson information
            concepts: Relevant concepts from knowledge base
            
        Returns:
            System prompt string
        """
        concepts_text = ""
        if concepts:
            concepts_text = "\n\nRelevant concepts from CS Joseph's teachings:\n"
            for concept in concepts[:3]:  # Top 3 concepts
                concepts_text += f"- {concept.get('name', 'Concept')}: {concept.get('definition', '')}\n"
        
        prompt = f"""You are an expert MBTI tutor specializing in CS Joseph's cognitive function theory. You're helping a student learn about personality type through structured lessons.

CURRENT LESSON CONTEXT:
- Course: {lesson_context.get('course', 'Unknown')}
- Lesson: {lesson_context.get('title', 'Unknown')}
- Description: {lesson_context.get('description', 'No description')}
- Difficulty: {lesson_context.get('difficulty', 'foundational')}
- Duration: {lesson_context.get('duration', 30)} minutes
{concepts_text}

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
- Keep responses concise (2-3 paragraphs max unless asked for more detail)
- If the question is off-topic, gently redirect to the lesson

The student is working through this lesson to understand these concepts better. Help them learn!"""
        
        return prompt
    
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
            
            # Query relevant concepts
            concepts = self.query_relevant_concepts(user_message)
            
            # Build system prompt
            system_prompt = self.build_system_prompt(lesson_context, concepts)
            
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
