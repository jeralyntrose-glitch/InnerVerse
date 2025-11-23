"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2025-11-23

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database tables"""
    
    # API Usage Tracking
    op.create_table(
        'api_usage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('operation', sa.String(100), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('input_tokens', sa.Integer(), server_default='0'),
        sa.Column('output_tokens', sa.Integer(), server_default='0'),
        sa.Column('cost', sa.Numeric(10, 6), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_api_usage_timestamp', 'api_usage', ['timestamp'], postgresql_ops={'timestamp': 'DESC'})
    
    # Lesson Concepts
    op.create_table(
        'lesson_concepts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lesson_id', postgresql.UUID(), nullable=False),
        sa.Column('concept_id', sa.String(255), nullable=False),
        sa.Column('concept_name', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Numeric(3, 2)),
        sa.Column('similarity_score', sa.Numeric(5, 4)),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lesson_id', 'concept_id', name='uq_lesson_concept')
    )
    op.create_index('idx_lesson_concepts_lesson', 'lesson_concepts', ['lesson_id'])
    op.create_index('idx_lesson_concepts_concept', 'lesson_concepts', ['concept_id'])
    
    # Chat Threads
    op.create_table(
        'chat_threads',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('course_id', postgresql.UUID(), nullable=False),
        sa.Column('lesson_id', postgresql.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('message_count', sa.Integer(), server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('course_id', 'lesson_id', name='uq_course_lesson')
    )
    
    # Chat Messages
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('thread_id', postgresql.UUID(), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tokens_input', sa.Integer()),
        sa.Column('tokens_output', sa.Integer()),
        sa.Column('cost', sa.Numeric(10, 6)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['thread_id'], ['chat_threads.id'], ondelete='CASCADE'),
        sa.CheckConstraint("role IN ('user', 'assistant')", name='check_chat_role')
    )
    op.create_index('idx_chat_messages_thread', 'chat_messages', ['thread_id', 'created_at'])
    
    # Background Jobs
    op.create_table(
        'background_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('request_payload', sa.JSON()),
        sa.Column('response_result', sa.JSON()),
        sa.Column('error_message', sa.Text()),
        sa.Column('conversation_id', sa.Integer()),
        sa.Column('lesson_id', postgresql.UUID()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_background_jobs_status', 'background_jobs', ['status', 'created_at'])
    
    # Conversations
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.Text()),
        sa.Column('project_id', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Messages
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), server_default='completed'),
        sa.Column('input_tokens', sa.Integer()),
        sa.Column('output_tokens', sa.Integer()),
        sa.Column('cost', sa.Numeric(10, 6)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE')
    )
    op.create_index('idx_messages_conversation', 'messages', ['conversation_id', 'created_at'])
    
    # YouTube Pending Links
    op.create_table(
        'youtube_pending_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('youtube_url', sa.Text(), nullable=False),
        sa.Column('video_title', sa.Text()),
        sa.Column('channel', sa.Text()),
        sa.Column('duration', sa.Text()),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('document_id', sa.Text()),
        sa.Column('chunks_count', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('youtube_url', name='uq_youtube_url')
    )


def downgrade() -> None:
    """Drop all tables"""
    op.drop_table('youtube_pending_links')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('background_jobs')
    op.drop_table('chat_messages')
    op.drop_table('chat_threads')
    op.drop_table('lesson_concepts')
    op.drop_table('api_usage')

