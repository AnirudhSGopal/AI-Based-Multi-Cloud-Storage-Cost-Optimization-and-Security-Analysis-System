import os
import pytest
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(".env")

# Must ONLY run against dedicated TEST_DATABASE_URL, never against production/live DATABASE_URL
PG_URL = os.getenv("TEST_DATABASE_URL")
if PG_URL and PG_URL.startswith("postgres://"):
    PG_URL = "postgresql://" + PG_URL[len("postgres://"):]

can_test_postgres = bool(PG_URL and "postgresql" in PG_URL)


@pytest.mark.skipif(not can_test_postgres, reason="TEST_DATABASE_URL (PostgreSQL) is not set; skipping live DB test")
def test_postgres_audit_log_append_only_trigger():
    """Prove raw UPDATE/DELETE on audit_logs fail on Postgres and user deletion still nulls actor_id."""
    engine = create_engine(PG_URL)
    with engine.connect() as conn:
        # 1. Create a test user
        conn.execute(text("""
            INSERT INTO users (username, email, password_hash, role, is_active, created_at, updated_at)
            VALUES ('pg_immut_test', 'pg_immut_test@cloudopt.ai', 'dummy_hash', 'viewer', true, NOW(), NOW())
            ON CONFLICT (email) DO UPDATE SET is_active=true RETURNING id;
        """))
        res = conn.execute(text("SELECT id FROM users WHERE email='pg_immut_test@cloudopt.ai'")).fetchone()
        user_id = res[0]

        # 2. Insert audit log referencing this user
        conn.execute(text(f"""
            INSERT INTO audit_logs (actor_id, actor_email, actor_role, event_type, status, details, created_at)
            VALUES ({user_id}, 'pg_immut_test@cloudopt.ai', 'viewer', 'test.pg_immutability', 'success', '{{}}'::jsonb, NOW());
        """))
        log_res = conn.execute(text(f"SELECT id FROM audit_logs WHERE actor_id={user_id} ORDER BY id DESC LIMIT 1")).fetchone()
        log_id = log_res[0]
        conn.commit()

        # 3. Raw UPDATE MUST fail due to DB trigger
        update_failed = False
        try:
            conn.execute(text(f"UPDATE audit_logs SET status='tampered' WHERE id={log_id}"))
            conn.commit()
        except Exception as exc:
            conn.rollback()
            update_failed = True
            assert "append-only" in str(exc).lower()
        assert update_failed, "Raw UPDATE on audit_logs should have been blocked by trigger"

        # 4. Raw DELETE MUST fail due to DB trigger
        delete_failed = False
        try:
            conn.execute(text(f"DELETE FROM audit_logs WHERE id={log_id}"))
            conn.commit()
        except Exception as exc:
            conn.rollback()
            delete_failed = True
            assert "immutable" in str(exc).lower()
        assert delete_failed, "Raw DELETE on audit_logs should have been blocked by trigger"

        # 5. User deletion MUST cascade ON DELETE SET NULL to actor_id without failing trigger
        conn.execute(text(f"DELETE FROM users WHERE id={user_id}"))
        conn.commit()

        check_res = conn.execute(text(f"SELECT id, actor_id, actor_email FROM audit_logs WHERE id={log_id}")).fetchone()
        assert check_res[1] is None, f"Expected actor_id to be NULL after user deletion, got {check_res[1]}"
        assert check_res[2] == "pg_immut_test@cloudopt.ai"

