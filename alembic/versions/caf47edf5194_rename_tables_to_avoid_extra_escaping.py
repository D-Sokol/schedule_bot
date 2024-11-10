"""Rename tables to avoid extra escaping

Revision ID: caf47edf5194
Revises: 9431e8cc4de8
Create Date: 2024-11-10 18:51:18.986876

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'caf47edf5194'
down_revision: Union[str, None] = '9431e8cc4de8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("user", "users")
    op.rename_table("element", "elements")


def downgrade() -> None:
    op.rename_table("users", "user")
    op.rename_table("elements", "element")
