"""
InnerVerse Learning Paths - UI Routes
======================================
Serves the 2D canvas UI pages.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import os

router = APIRouter(prefix="/learning-paths", tags=["Learning Paths UI"])

@router.get("", response_class=HTMLResponse)
async def learning_paths_index():
    """
    Serve the main learning paths canvas page.
    
    Returns HTML with embedded D3.js tree visualization.
    """
    html_path = os.path.join('static', 'learning_paths.html')
    
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Learning Paths page not found</h1>",
            status_code=404
        )


@router.get("/{course_id}", response_class=HTMLResponse)
async def course_detail_page(course_id: str):
    """
    Serve course detail page (Phase 4 - placeholder for now).
    
    Args:
        course_id: Course UUID
        
    Returns:
        HTML page with course details
    """
    return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Course Details - InnerVerse</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    margin: 0;
                    background: #f8fafc;
                }}
                .message {{
                    text-align: center;
                    padding: 2rem;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.1);
                }}
                h1 {{ color: #6366f1; }}
                p {{ color: #64748b; }}
                a {{ color: #6366f1; text-decoration: none; font-weight: 600; }}
            </style>
        </head>
        <body>
            <div class="message">
                <h1>📖 Course Detail Page</h1>
                <p>Course ID: <code>{course_id}</code></p>
                <p>This page will be implemented in Phase 4!</p>
                <br>
                <a href="/learning-paths">← Back to Learning Paths</a>
            </div>
        </body>
        </html>
    """)


@router.get("/{course_id}/{lesson_id}", response_class=HTMLResponse)
async def lesson_page(course_id: str, lesson_id: str):
    """
    Serve lesson page with split-screen layout (Phase 4 - placeholder).
    
    Args:
        course_id: Course UUID
        lesson_id: Lesson UUID
        
    Returns:
        HTML page with lesson content and chat integration
    """
    return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Lesson - InnerVerse</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    margin: 0;
                    background: #f8fafc;
                }}
                .message {{
                    text-align: center;
                    padding: 2rem;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.1);
                    max-width: 500px;
                }}
                h1 {{ color: #6366f1; }}
                p {{ color: #64748b; margin: 0.5rem 0; }}
                code {{ 
                    background: #f1f5f9; 
                    padding: 2px 6px; 
                    border-radius: 4px;
                    font-size: 12px;
                }}
                a {{ color: #6366f1; text-decoration: none; font-weight: 600; }}
            </style>
        </head>
        <body>
            <div class="message">
                <h1>📚 Lesson Page</h1>
                <p>Course: <code>{course_id}</code></p>
                <p>Lesson: <code>{lesson_id}</code></p>
                <br>
                <p>Split-screen lesson view with chat integration</p>
                <p style="color: #94a3b8; font-size: 14px;">Coming in Phase 4!</p>
                <br>
                <a href="/learning-paths">← Back to Learning Paths</a>
            </div>
        </body>
        </html>
    """)
