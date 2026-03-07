"""Initial schema with integer IDs

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-03-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create chats table
    op.create_table('chats',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='User ID (reference only, no FK)'),
        sa.Column('owner_profile_id', sa.Integer(), nullable=False, comment='Owner Profile ID (reference only, no FK)'),
        sa.Column('status', sa.String(length=20), nullable=False, comment='Chat status: active, closed'),
        sa.Column('last_message_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp of last message for session continuity'),
        sa.Column('flow_state', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Structured booking state (property_id, service_id, date, time, etc.)'),
        sa.Column('bot_memory', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Unstructured AI context and conversation history'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Chat creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Last update timestamp'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_status', 'chats', ['status'], unique=False, postgresql_using='btree')
    op.create_index('idx_user_owner_last_message', 'chats', ['user_id', 'owner_profile_id', 'last_message_at'], unique=False, postgresql_using='btree')
    
    # Create messages table
    op.create_table('messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chat_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Chat session ID'),
        sa.Column('sender_type', sa.String(length=20), nullable=False, comment='Message sender: user, bot, system'),
        sa.Column('message_type', sa.String(length=20), nullable=False, comment='Message format: text, button, list, media'),
        sa.Column('content', sa.Text(), nullable=False, comment='Message text content'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Message-specific data'),
        sa.Column('token_usage', sa.Integer(), nullable=True, comment='LLM token count for cost tracking'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Message creation timestamp'),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_chat_created', 'messages', ['chat_id', 'created_at'], unique=False, postgresql_using='btree')


def downgrade():
    op.drop_index('idx_chat_created', table_name='messages', postgresql_using='btree')
    op.drop_table('messages')
    op.drop_index('idx_user_owner_last_message', table_name='chats', postgresql_using='btree')
    op.drop_index('idx_status', table_name='chats', postgresql_using='btree')
    op.drop_table('chats')
