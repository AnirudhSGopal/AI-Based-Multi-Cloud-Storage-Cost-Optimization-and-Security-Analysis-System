"""add_totp_last_timestep

Revision ID: c3a44750dee0
Revises: d8b5f9e23a4c
Create Date: 2026-10-14 16:36:47.355276

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3a44750dee0'
down_revision = 'd8b5f9e23a4c'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('totp_last_timestep', sa.BigInteger(), nullable=True))


def downgrade():
    op.drop_column('users', 'totp_last_timestep')
