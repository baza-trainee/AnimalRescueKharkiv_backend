"""Update User lazy-loads relationships settings

Revision ID: c8d5da9b3031
Revises: 2aa494874702
Create Date: 2024-07-31 13:22:32.702279

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8d5da9b3031'
down_revision: Union[str, None] = '2aa494874702'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###