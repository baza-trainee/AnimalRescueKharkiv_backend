from typing import Sequence, Union
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e71354e4b787'
down_revision: Union[str, None] = 'a127cc5ca963'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add the column without setting nullable=False initially
    op.add_column('users', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()))

    # Fill existing NULL values with timezone-aware datetime
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE users
        SET created_at = :now
        WHERE created_at IS NULL
    """), {"now": datetime.now(timezone.utc)})

    # Alter the column to set nullable=False after filling in values
    op.alter_column('users', 'created_at', nullable=False)

    # Create an index on the new column
    op.create_index(op.f('ix_users_created_at'), 'users', ['created_at'], unique=False)

def downgrade() -> None:
    # Drop the index and column if downgrading
    op.drop_index(op.f('ix_users_created_at'), table_name='users')
    op.drop_column('users', 'created_at')
