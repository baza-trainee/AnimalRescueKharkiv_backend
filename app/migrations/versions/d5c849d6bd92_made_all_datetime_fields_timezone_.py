from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision: str = 'd5c849d6bd92'
down_revision: Union[str, None] = 'e71354e4b787'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Convert existing timestamps to UTC timezone explicitly
    op.execute("ALTER TABLE crm_animals ALTER COLUMN updated_at SET DATA TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE crm_animals ALTER COLUMN created_at SET DATA TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE media_assets ALTER COLUMN created_at SET DATA TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE media_assets ALTER COLUMN updated_at SET DATA TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC'")

    # Alter columns to enforce timezone-aware timestamps with defaults and onupdate
    op.alter_column('crm_animals', 'updated_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False,
               server_default=func.now(),
               onupdate=func.now())
    op.alter_column('crm_animals', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False,
               server_default=func.now())
    op.alter_column('media_assets', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               server_default=func.now())
    op.alter_column('media_assets', 'updated_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               server_default=func.now(),
               onupdate=func.now())

def downgrade() -> None:
    # Revert columns to timestamp without timezone
    op.alter_column('media_assets', 'updated_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True,
               server_default=None,
               onupdate=None)
    op.alter_column('media_assets', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True,
               server_default=None)
    op.alter_column('crm_animals', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False,
               server_default=None)
    op.alter_column('crm_animals', 'updated_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False,
               server_default=None,
               onupdate=None)
