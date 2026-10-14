"""add used_refresh_tokens and totp_secret

Revision ID: d8b5f9e23a4c
Revises: c7a4e8d12f3b
Create Date: 2026-10-14 12:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd8b5f9e23a4c'
down_revision = 'c7a4e8d12f3b'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add totp_secret to users table
    op.add_column('users', sa.Column('totp_secret', sa.String(length=64), nullable=True))

    # 2. Add used_refresh_tokens table for rotation & reuse detection
    op.create_table(
        'used_refresh_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('jti', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_used_refresh_tokens_jti'), 'used_refresh_tokens', ['jti'], unique=True)
    op.create_index(op.f('ix_used_refresh_tokens_user_id'), 'used_refresh_tokens', ['user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_used_refresh_tokens_user_id'), table_name='used_refresh_tokens')
    op.drop_index(op.f('ix_used_refresh_tokens_jti'), table_name='used_refresh_tokens')
    op.drop_table('used_refresh_tokens')
    op.drop_column('users', 'totp_secret')

