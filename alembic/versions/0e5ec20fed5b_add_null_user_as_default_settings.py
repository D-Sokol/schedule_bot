"""Add null user as default settings

Revision ID: 0e5ec20fed5b
Revises: bcebcdbc8804
Create Date: 2025-01-05 17:21:58.510202

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0e5ec20fed5b"
down_revision: Union[str, None] = "bcebcdbc8804"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_LAST_SCHEDULE = """
Пн 10:00 (важное) Бег
Пн 11:30 Отжимания
Пт 18:00 (важное,вечер) Сходить в бар
""".strip()
DEFAULT_USER_TEMPLATE = "{}"


def upgrade() -> None:
    op.execute(
        sa.insert(
            sa.table(
                "users",
                sa.column("tg_id"),
                sa.column("is_admin"),
                sa.column("last_schedule"),
                sa.column("user_template"),
            )
        ).values(
            tg_id=0,
            is_admin=False,
            last_schedule=DEFAULT_LAST_SCHEDULE,
            user_template=DEFAULT_USER_TEMPLATE,
        )
    )


def downgrade() -> None:
    op.execute(sa.delete(sa.table("users", sa.column("tg_id"))).where(sa.column("tg_id") == 0))
