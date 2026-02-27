"""create_chats_and_messages_tables

Revision ID: fa621615d4fa
Revises: 8351becbdbe8
Create Date: 2026-02-27 13:29:48.437642

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = 'fa621615d4fa'
down_revision = '8351becbdbe8'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create chats and messages tables for the async chat database.
    Drop the old chat_messages table.
    """
    # Create chats table
    op.create_table(
        'chats',
        sa.Column('id', sa.UUID(), nullable=False, default=uuid.uuid4, comment='Unique chat identifier'),
        sa.Column('user_id', sa.UUID(), nullable=False, comment='User ID (reference only, no FK)'),
        sa.Column('owner_id', sa.UUID(), nullable=False, comment='Owner ID (reference only, no FK)'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active', comment='Chat status: active, closed'),
        sa.Column('last_message_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp of last message for session continuity'),
        sa.Column('flow_state', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}', comment='Structured booking state (property_id, service_id, date, time, etc.)'),
        sa.Column('bot_memory', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}', comment='Unstructured AI context and conversation history'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Chat creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Last update timestamp'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for chats table
    op.create_index('idx_status', 'chats', ['status'], unique=False, postgresql_using='btree')
    op.create_index('idx_user_owner_last_message', 'chats', ['user_id', 'owner_id', 'last_message_at'], unique=False, postgresql_using='btree')
    op.create_index(op.f('ix_chats_owner_id'), 'chats', ['owner_id'], unique=False)
    op.create_index(op.f('ix_chats_user_id'), 'chats', ['user_id'], unique=False)
    
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.UUID(), nullable=False, default=uuid.uuid4, comment='Unique message identifier'),
        sa.Column('chat_id', sa.UUID(), nullable=False, comment='Foreign key to chat session'),
        sa.Column('sender_type', sa.String(length=20), nullable=False, comment='Message sender: user, bot, system'),
        sa.Column('message_type', sa.String(length=20), nullable=False, server_default='text', comment='Message format: text, button, list, media'),
        sa.Column('content', sa.Text(), nullable=False, comment='Message text content'),
        sa.Column('message_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}', comment='Message-specific data (buttons, lists, media URLs, etc.)'),
        sa.Column('token_usage', sa.Integer(), nullable=True, comment='LLM token count for cost tracking'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Message creation timestamp'),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for messages table
    op.create_index('idx_chat_created', 'messages', ['chat_id', 'created_at'], unique=False, postgresql_using='btree')
    op.create_index(op.f('ix_messages_chat_id'), 'messages', ['chat_id'], unique=False)
    
    # Drop old chat_messages table
    op.drop_index(op.f('ix_chat_messages_user_id'), table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_id'), table_name='chat_messages')
    op.drop_table('chat_messages')


def downgrade():
    """
    Restore the old chat_messages table and drop chats and messages tables.
    """
    # Recreate old chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
        sa.Column('message', sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column('response', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint('id', name='chat_messages_pkey')
    )
    op.create_index('ix_chat_messages_user_id', 'chat_messages', ['user_id'], unique=False)
    op.create_index('ix_chat_messages_id', 'chat_messages', ['id'], unique=False)
    
    # Drop new tables
    op.drop_index(op.f('ix_messages_chat_id'), table_name='messages')
    op.drop_index('idx_chat_created', table_name='messages', postgresql_using='btree')
    op.drop_table('messages')
    
    op.drop_index(op.f('ix_chats_user_id'), table_name='chats')
    op.drop_index(op.f('ix_chats_owner_id'), table_name='chats')
    op.drop_index('idx_user_owner_last_message', table_name='chats', postgresql_using='btree')
    op.drop_index('idx_status', table_name='chats', postgresql_using='btree')
    op.drop_table('chats')
