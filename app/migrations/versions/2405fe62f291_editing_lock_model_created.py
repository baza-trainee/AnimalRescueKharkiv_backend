"""Editing lock model created

Revision ID: 2405fe62f291
Revises: 844c46eae7dc
Create Date: 2025-02-06 18:01:16.568080

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2405fe62f291'
down_revision: Union[str, None] = '844c46eae7dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('crm_editing_locks',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('animal_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('section_name', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['animal_id'], ['crm_animals.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_crm_editing_locks_created_at'), 'crm_editing_locks', ['created_at'], unique=False)
    op.create_index(op.f('ix_crm_editing_locks_section_name'), 'crm_editing_locks', ['section_name'], unique=False)
    op.create_unique_constraint('crm_locations_name_key', 'crm_locations', ['name'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('crm_locations_name_key', 'crm_locations', type_='unique')
    op.drop_index(op.f('ix_crm_editing_locks_section_name'), table_name='crm_editing_locks')
    op.drop_index(op.f('ix_crm_editing_locks_created_at'), table_name='crm_editing_locks')
    op.drop_table('crm_editing_locks')
    # ### end Alembic commands ###
