"""Security token model created

Revision ID: eab61bf2f5b6
Revises: b50b11a78a92
Create Date: 2024-10-01 00:19:39.198427

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eab61bf2f5b6'
down_revision: Union[str, None] = 'b50b11a78a92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('security_tokens',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('token', sa.String(length=500), nullable=False),
    sa.Column('token_type', sa.Enum('access', 'invitation', 'reset', 'refresh', name='tokentype'), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('expire_on', sa.DateTime(timezone=True), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='cascade'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_security_tokens_created_at'), 'security_tokens', ['created_at'], unique=False)
    op.create_index(op.f('ix_security_tokens_expire_on'), 'security_tokens', ['expire_on'], unique=False)
    op.create_index(op.f('ix_security_tokens_token'), 'security_tokens', ['token'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_security_tokens_token'), table_name='security_tokens')
    op.drop_index(op.f('ix_security_tokens_expire_on'), table_name='security_tokens')
    op.drop_index(op.f('ix_security_tokens_created_at'), table_name='security_tokens')
    op.drop_table('security_tokens')
    # ### end Alembic commands ###