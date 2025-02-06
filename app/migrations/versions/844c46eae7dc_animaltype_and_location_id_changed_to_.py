"""AnimalType and Location Id changed to int

Revision ID: 844c46eae7dc
Revises: 28dca6fafab6
Create Date: 2025-02-04 18:54:53.506084

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '844c46eae7dc'
down_revision: Union[str, None] = '28dca6fafab6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the current index before renaming tables
    op.drop_index('ix_crm_animal_types_name', table_name='crm_animal_types')
    # Rename original tables to temporary names
    op.rename_table('crm_animal_types', 'crm_animal_types_tmp')
    op.rename_table('crm_locations', 'crm_locations_tmp')

    # Create new tables with integer autoincrement IDs
    op.create_table('crm_animal_types',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_crm_animal_types_name', 'crm_animal_types', ['name'], unique=True)

    op.create_table('crm_locations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Update references in crm_animals and crm_animal_locations
    op.add_column('crm_animals', sa.Column('general__animal_type_id_tmp', sa.Integer(), nullable=True))
    op.add_column('crm_animal_locations', sa.Column('location_id_tmp', sa.Integer(), nullable=False))


    # Drop old columns and rename the new ones
    op.drop_constraint('crm_animals_general__animal_type_id_fkey', 'crm_animals', type_='foreignkey')
    op.drop_column('crm_animals', 'general__animal_type_id')
    op.alter_column('crm_animals', 'general__animal_type_id_tmp', new_column_name='general__animal_type_id')

    op.drop_constraint('crm_animal_locations_location_id_fkey', 'crm_animal_locations', type_='foreignkey')
    op.drop_column('crm_animal_locations', 'location_id')
    op.alter_column('crm_animal_locations', 'location_id_tmp', new_column_name='location_id')

    # Recreate foreign key constraints
    op.create_foreign_key('crm_animals_general__animal_type_id_fkey', 'crm_animals', 'crm_animal_types', ['general__animal_type_id'], ['id'])
    op.create_foreign_key('crm_animal_locations_location_id_fkey', 'crm_animal_locations', 'crm_locations', ['location_id'], ['id'])

    # Drop the old temporary tables
    op.drop_table('crm_animal_types_tmp')
    op.drop_table('crm_locations_tmp')


def downgrade() -> None:
    # Drop the current index before renaming tables
    op.drop_index('ix_crm_animal_types_name', table_name='crm_animal_types')

    # Rename current tables to temporary names
    op.rename_table('crm_animal_types', 'crm_animal_types_tmp')
    op.rename_table('crm_locations', 'crm_locations_tmp')

    # Recreate the original tables with UUIDs
    op.create_table('crm_animal_types',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_crm_animal_types_name', 'crm_animal_types', ['name'], unique=True)

    op.create_table('crm_locations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Data migration back to UUID version is skipped as UUID restoration is complex without exact values
    op.drop_table('crm_animal_types_tmp')
    op.drop_table('crm_locations_tmp')
