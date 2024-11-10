"""Create tables

Revision ID: 9431e8cc4de8
Revises: 
Create Date: 2024-11-10 18:35:15.682435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9431e8cc4de8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user',
    sa.Column('tg_id', sa.BigInteger(), nullable=False),
    sa.Column('is_admin', sa.Boolean(), nullable=False),
    sa.Column('last_schedule', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('tg_id')
    )
    op.create_table('element',
    sa.Column('element_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=True),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('file_id_photo', sa.String(length=83), nullable=True),
    sa.Column('file_id_document', sa.String(length=71), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.tg_id'], ),
    sa.PrimaryKeyConstraint('element_id'),
    sa.UniqueConstraint('user_id', 'name', name='u_name_user')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('element')
    op.drop_table('user')
    # ### end Alembic commands ###
