"""Merging security token and title field heads

Revision ID: 2741cc423102
Revises: 1420108466c8, eab61bf2f5b6
Create Date: 2024-11-05 23:47:49.252847

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2741cc423102'
down_revision: Union[Sequence[str], None] = ('1420108466c8', 'eab61bf2f5b6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
