"""add provider column

Revision ID: fcf11c289888
Revises: eca99ae2598e
Create Date: 2020-12-14 12:03:49.323396

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fcf11c289888'
down_revision = 'eca99ae2598e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('provider', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'provider')
    # ### end Alembic commands ###