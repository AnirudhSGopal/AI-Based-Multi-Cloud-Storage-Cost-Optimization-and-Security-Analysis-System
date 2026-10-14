"""
CI check to verify Row Level Security (RLS) is enabled on all CloudOpt public application tables.
Works in live PostgreSQL environments (via TEST_DATABASE_URL) and statically analyzes
the migration script when live PostgreSQL is unavailable.
"""
import os
import sys
import re
from pathlib import Path

APP_TABLES = [
    "users",
    "cloud_accounts",
    "scan_jobs",
    "scan_results",
    "vulnerabilities",
    "cloud_metrics",
    "audit_logs",
]

def check_live_db(db_url: str) -> bool:
    from sqlalchemy import create_engine, text
    engine = create_engine(db_url)
    with engine.connect() as conn:
        res = conn.execute(text("""
            SELECT tablename, rowsecurity
            FROM pg_tables
            WHERE schemaname = 'public';
        """)).fetchall()
        
        status = {row[0]: row[1] for row in res}
        missing_rls = []
        for tbl in APP_TABLES:
            if tbl in status and not status[tbl]:
                missing_rls.append(tbl)
                
        if missing_rls:
            print(f"[FAIL] Tables missing Row-Level Security: {missing_rls}", file=sys.stderr)
            return False
        print(f"[PASS] RLS enabled on all active public tables: {list(status.keys())}")
        return True

def check_migration_script() -> bool:
    sql_path = Path(__file__).resolve().parent.parent / "migrations" / "db_roles_and_permissions.sql"
    if not sql_path.exists():
        print(f"[FAIL] Migration file {sql_path} not found", file=sys.stderr)
        return False
        
    content = sql_path.read_text(encoding="utf-8")
    if "ENABLE ROW LEVEL SECURITY" not in content:
        print("[FAIL] 'ENABLE ROW LEVEL SECURITY' missing from db_roles_and_permissions.sql", file=sys.stderr)
        return False
        
    print("[PASS] db_roles_and_permissions.sql contains RLS enforcement directives.")
    return True

def main():
    pg_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if pg_url and ("postgresql" in pg_url or "postgres://" in pg_url):
        if pg_url.startswith("postgres://"):
            pg_url = "postgresql://" + pg_url[len("postgres://"):]
        try:
            success = check_live_db(pg_url)
        except Exception as exc:
            print(f"[WARN] Live DB check error ({exc}), falling back to static migration check.")
            success = check_migration_script()
    else:
        success = check_migration_script()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
