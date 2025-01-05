"""Add field for bans

Revision ID: 91fead7b82ab
Revises: 0e5ec20fed5b
Create Date: 2025-01-05 19:30:20.111364

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '91fead7b82ab'
down_revision: Union[str, None] = '0e5ec20fed5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('is_banned', sa.Boolean(), server_default='false', nullable=False))
    op.alter_column('users', 'is_admin', server_default='false', existing_server_default=None)


def downgrade() -> None:
    op.drop_column('users', 'is_banned')
    op.alter_column('users', 'is_admin', server_default=None, existing_server_default='false')
