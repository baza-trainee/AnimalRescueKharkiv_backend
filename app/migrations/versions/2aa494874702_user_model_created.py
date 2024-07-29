"""User model created

Revision ID: 2aa494874702
Revises: d8a7d9555940
Create Date: 2024-07-29 16:43:34.086446

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils


# revision identifiers, used by Alembic.
revision: str = '2aa494874702'
down_revision: Union[str, None] = 'd8a7d9555940'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('email', sqlalchemy_utils.types.email.EmailType(length=255), nullable=False),
    sa.Column('domain', sa.String(length=20), nullable=False),
    sa.Column('password', sqlalchemy_utils.types.password.PasswordType(max_length=1024), nullable=False),
    sa.Column('role_id', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email', 'domain', name='email_domain_unique'),
    sa.UniqueConstraint('username', 'domain', name='username_domain_unique')
    )
    op.create_index(op.f('ix_users_domain'), 'users', ['domain'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_domain'), table_name='users')
    op.drop_table('users')
    # ### end Alembic commands ###