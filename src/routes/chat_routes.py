"""
Chat Routes - API endpoints for lesson chat
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import os
from ..services.chat_service import ChatService
from ..services.knowledge_graph_manager import KnowledgeGraphManager

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')

# Pydantic models
class ChatRequest(BaseModel):
    course_id: str
    lesson_id: str
    message: str

class ChatResponse(BaseModel):
    success: bool
    message: str
    thread_id: Optional[str] = None
    tokens: Optional[dict] = None
    cost: Optional[float] = None
    error: Optional[str] = None

class ChatHistoryResponse(BaseModel):
    success: bool
    messages: List[dict]
    stats: Optional[dict] = None


@router.post("/lesson", response_model=ChatResponse)
async def chat_with_lesson(request: ChatRequest):
    """
    Send message to AI tutor with lesson context
    
    Request body:
    - course_id: Course UUID
    - lesson_id: Lesson UUID
    - message: User's message
    
    Returns:
    - AI response with token usage and cost
    """
    try:
        # Initialize services
        kg_manager = KnowledgeGraphManager()
        chat_service = ChatService(DATABASE_URL, kg_manager)
        
        # Process chat
        result = await chat_service.chat(
            course_id=request.course_id,
            lesson_id=request.lesson_id,
            user_message=request.message
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        print(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lesson/{lesson_id}/history", response_model=ChatHistoryResponse)
async def get_lesson_chat_history(lesson_id: str):
    """
    Get chat history for a lesson
    
    Args:
        lesson_id: Lesson UUID
        
    Returns:
        List of messages and thread statistics
    """
    try:
        # Initialize services
        kg_manager = KnowledgeGraphManager()
        chat_service = ChatService(DATABASE_URL, kg_manager)
        
        # Get thread
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM chat_threads WHERE lesson_id = %s",
                (lesson_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return ChatHistoryResponse(
                    success=True,
                    messages=[],
                    stats={'message_count': 0}
                )
            
            thread_id = row[0]
            
            # Get history and stats
            messages = chat_service.get_chat_history(thread_id, limit=50)
            stats = chat_service.get_thread_stats(thread_id)
            
            return ChatHistoryResponse(
                success=True,
                messages=messages,
                stats=stats
            )
        finally:
            conn.close()
        
    except Exception as e:
        print(f"Get history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/lesson/{lesson_id}/history")
async def clear_lesson_chat(lesson_id: str):
    """
    Clear chat history for a lesson
    
    Args:
        lesson_id: Lesson UUID
        
    Returns:
        Success confirmation
    """
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        try:
            cursor = conn.cursor()
            # Delete thread (cascade will delete messages)
            cursor.execute("DELETE FROM chat_threads WHERE lesson_id = %s", (lesson_id,))
            conn.commit()
            
            return {'success': True, 'message': 'Chat history cleared'}
        finally:
            conn.close()
        
    except Exception as e:
        print(f"Clear history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
