"""convert_sport_type_to_array_enum

Revision ID: 2756be45c341
Revises: 11804d708e18
Create Date: 2026-03-09 18:19:34.657153

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2756be45c341'
down_revision: Union[str, Sequence[str], None] = '11804d708e18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create ENUM type for sport types
    op.execute("""
        CREATE TYPE sporttype AS ENUM (
            'futsal', 'football', 'cricket', 'hockey', 
            'padel', 'badminton', 'tennis'
        )
    """)
    
    # 2. Add new sport_types column (array of enums, nullable for now)
    op.execute("""
        ALTER TABLE courts 
        ADD COLUMN sport_types sporttype[]
    """)
    
    # 3. Migrate existing data: convert sport_type string to sport_types array
    # If sport_type exists and is valid, convert it to array
    # Otherwise, default to ['cricket']
    op.execute("""
        UPDATE courts 
        SET sport_types = CASE 
            WHEN sport_type IN ('futsal', 'football', 'cricket', 'hockey', 'padel', 'badminton', 'tennis')
            THEN ARRAY[sport_type::sporttype]
            ELSE ARRAY['cricket'::sporttype]
        END
    """)
    
    # 4. Make sport_types non-nullable
    op.execute("""
        ALTER TABLE courts 
        ALTER COLUMN sport_types SET NOT NULL
    """)
    
    # 5. Drop old sport_type column
    op.drop_column('courts', 'sport_type')


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Add back sport_type column
    op.add_column('courts', sa.Column('sport_type', sa.String(50), nullable=True))
    
    # 2. Convert array back to string (take first element)
    op.execute("""
        UPDATE courts 
        SET sport_type = sport_types[1]::text
    """)
    
    # 3. Make sport_type non-nullable
    op.execute("""
        ALTER TABLE courts 
        ALTER COLUMN sport_type SET NOT NULL
    """)
    
    # 4. Drop sport_types column
    op.drop_column('courts', 'sport_types')
    
    # 5. Drop ENUM type
    op.execute('DROP TYPE sporttype')
