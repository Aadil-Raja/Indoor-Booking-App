"""Update property to link to owner_profile instead of user

Revision ID: update_property_owner
Revises: 3becb2b9ac29
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'update_property_owner'
down_revision = '3becb2b9ac29'
branch_labels = None
depends_on = None


def upgrade():
    # Add new owner_profile_id column
    op.add_column('properties', sa.Column('owner_profile_id', sa.Integer(), nullable=True))
    
    # Migrate data: set owner_profile_id based on owner_id
    # This assumes each user with role='owner' has an owner_profile
    op.execute("""
        UPDATE properties p
        SET owner_profile_id = op.id
        FROM owner_profiles op
        WHERE op.user_id = p.owner_id
    """)
    
    # Make owner_profile_id non-nullable after data migration
    op.alter_column('properties', 'owner_profile_id', nullable=False)
    
    # Create foreign key constraint
    op.create_foreign_key(
        'fk_properties_owner_profile_id',
        'properties', 'owner_profiles',
        ['owner_profile_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Create index on owner_profile_id
    op.create_index('ix_properties_owner_profile_id', 'properties', ['owner_profile_id'])
    
    # Drop old foreign key and column
    op.drop_constraint('properties_owner_id_fkey', 'properties', type_='foreignkey')
    op.drop_index('ix_properties_owner_id', 'properties')
    op.drop_column('properties', 'owner_id')


def downgrade():
    # Add back owner_id column
    op.add_column('properties', sa.Column('owner_id', sa.Integer(), nullable=True))
    
    # Migrate data back: set owner_id based on owner_profile_id
    op.execute("""
        UPDATE properties p
        SET owner_id = op.user_id
        FROM owner_profiles op
        WHERE op.id = p.owner_profile_id
    """)
    
    # Make owner_id non-nullable after data migration
    op.alter_column('properties', 'owner_id', nullable=False)
    
    # Create foreign key constraint
    op.create_foreign_key(
        'properties_owner_id_fkey',
        'properties', 'users',
        ['owner_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Create index on owner_id
    op.create_index('ix_properties_owner_id', 'properties', ['owner_id'])
    
    # Drop new foreign key and column
    op.drop_constraint('fk_properties_owner_profile_id', 'properties', type_='foreignkey')
    op.drop_index('ix_properties_owner_profile_id', 'properties')
    op.drop_column('properties', 'owner_profile_id')
