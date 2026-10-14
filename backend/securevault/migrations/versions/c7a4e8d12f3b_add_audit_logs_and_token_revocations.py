"""Add audit_logs and token_revocations tables with DB-level immutability trigger

Revision ID: c7a4e8d12f3b
Revises: 60f8a3d42b91
Create Date: 2026-10-14 11:25:00.000000

Data Retention & Archival Strategy:
-----------------------------------
1. audit_logs:
   - Hot retention in primary database: 90 days.
   - Compliance archival: Export logs older than 90 days to immutable cold storage
     (e.g., S3 Glacier / GCS Archive with Object Lock / WORM compliance) for 365+ days.
   - DB-level trigger enforces append-only semantics (no updates or deletes permitted
     except the foreign key SET NULL cascade when an actor user is deleted).

2. token_revocations:
   - Retention policy: 30 days (strictly matches JWT_REFRESH_TOKEN_EXPIRES = 30 days).
   - Any token issued before a revocation older than 30 days has already naturally expired;
     therefore, rows older than 30 days can be safely pruned by scheduled maintenance cron.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7a4e8d12f3b'
down_revision = '60f8a3d42b91'
branch_labels = None
depends_on = None


def upgrade():
    # ── 1. Create audit_logs table ────────────────────────────────────────────
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('actor_email', sa.String(length=120), nullable=True),
        sa.Column('actor_role', sa.String(length=32), server_default='unknown', nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('target_type', sa.String(length=64), nullable=True),
        sa.Column('target_id', sa.String(length=64), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=256), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='success', nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_actor_id'), 'audit_logs', ['actor_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_actor_email'), 'audit_logs', ['actor_email'], unique=False)
    op.create_index(op.f('ix_audit_logs_event_type'), 'audit_logs', ['event_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_ip_address'), 'audit_logs', ['ip_address'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_audit_logs_event_type_created_at'), 'audit_logs', ['event_type', 'created_at'], unique=False)

    # ── 2. Create token_revocations table ─────────────────────────────────────
    op.create_table(
        'token_revocations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_token_revocations_user_id'), 'token_revocations', ['user_id'], unique=False)

    # ── 3. PostgreSQL append-only immutability trigger ────────────────────────
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("""
        CREATE OR REPLACE FUNCTION audit_logs_immutable_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'audit_logs rows are immutable and cannot be deleted';
            ELSIF TG_OP = 'UPDATE' THEN
                -- Allow ONLY foreign key SET NULL cascade when actor user is deleted
                IF (OLD.actor_id IS NOT NULL AND NEW.actor_id IS NULL)
                   AND NEW.id = OLD.id
                   AND NEW.actor_email IS NOT DISTINCT FROM OLD.actor_email
                   AND NEW.actor_role IS NOT DISTINCT FROM OLD.actor_role
                   AND NEW.event_type IS NOT DISTINCT FROM OLD.event_type
                   AND NEW.target_type IS NOT DISTINCT FROM OLD.target_type
                   AND NEW.target_id IS NOT DISTINCT FROM OLD.target_id
                   AND NEW.ip_address IS NOT DISTINCT FROM OLD.ip_address
                   AND NEW.user_agent IS NOT DISTINCT FROM OLD.user_agent
                   AND NEW.status IS NOT DISTINCT FROM OLD.status
                   AND NEW.details::text IS NOT DISTINCT FROM OLD.details::text
                   AND NEW.created_at IS NOT DISTINCT FROM OLD.created_at THEN
                    RETURN NEW;
                ELSE
                    RAISE EXCEPTION 'audit_logs rows are append-only and cannot be modified';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON audit_logs;
        CREATE TRIGGER trg_audit_logs_immutable
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION audit_logs_immutable_trigger();
        """)


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON audit_logs;")
        op.execute("DROP FUNCTION IF EXISTS audit_logs_immutable_trigger();")

    op.drop_index(op.f('ix_token_revocations_user_id'), table_name='token_revocations')
    op.drop_table('token_revocations')

    op.drop_index(op.f('ix_audit_logs_event_type_created_at'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_ip_address'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_event_type'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_actor_email'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_actor_id'), table_name='audit_logs')
    op.drop_table('audit_logs')
