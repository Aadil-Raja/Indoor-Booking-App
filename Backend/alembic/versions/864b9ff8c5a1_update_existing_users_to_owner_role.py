"""update_existing_users_to_owner_role

Revision ID: 864b9ff8c5a1
Revises: 11804d708e18
Create Date: 2026-03-03 05:09:48.200346

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '864b9ff8c5a1'
down_revision: Union[str, Sequence[str], None] = '11804d708e18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update all existing users to have owner role."""
    # Update all existing users to have 'owner' role
    op.execute(
        """
        UPDATE users 
        SET role = 'owner' 
        WHERE role = 'customer' OR role IS NULL
        """
    )


def downgrade() -> None:
    """Revert users back to customer role."""
    # Revert all users back to customer role
    op.execute(
        """
        UPDATE users 
        SET role = 'customer' 
        WHERE role = 'owner'
        """
    )
