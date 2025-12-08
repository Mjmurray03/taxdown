#!/usr/bin/env python3
"""
Database Migration Script for Taxdown MVP
==========================================
Executes PostgreSQL migrations on Railway PostgreSQL database.

Features:
- Loads DATABASE_URL from .env using python-dotenv
- Connects to PostgreSQL using psycopg2
- Executes migrations in a transaction with rollback on error
- Handles PostGIS extension creation
- Reports success/failure with table counts

Usage:
    python src/etl/run_migration.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: python-dotenv not installed. Run: pip install python-dotenv")
    sys.exit(1)


def get_project_root() -> Path:
    """Get the project root directory (where .env file is located)."""
    # This script is in src/etl/, so go up two levels
    return Path(__file__).resolve().parent.parent.parent


def load_database_url() -> str:
    """Load DATABASE_URL from .env file or environment variable.

    Priority:
    1. DATABASE_URL_PUBLIC environment variable (for external access)
    2. DATABASE_URL environment variable
    3. DATABASE_URL from .env file

    Note: Railway's internal hostname (postgres.railway.internal) is only
    accessible from within Railway's network. For external access, use
    the public hostname provided by Railway.
    """
    project_root = get_project_root()
    env_path = project_root / ".env"

    if env_path.exists():
        load_dotenv(env_path)

    # Check for public URL first (for external access)
    database_url = os.getenv("DATABASE_URL_PUBLIC")
    if database_url:
        print("Using DATABASE_URL_PUBLIC (external access)")
    else:
        database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("ERROR: DATABASE_URL not found in environment or .env file")
        print("  Set DATABASE_URL_PUBLIC for external Railway access")
        sys.exit(1)

    # Check if using internal Railway hostname
    if "railway.internal" in database_url:
        print("WARNING: DATABASE_URL uses Railway internal hostname.")
        print("  This only works from within Railway's network.")
        print("  For external access, set DATABASE_URL_PUBLIC with the public hostname.")
        print("  Example: DATABASE_URL_PUBLIC=postgresql://postgres:PASSWORD@HOST.railway.app:PORT/railway")
        print("")
        print("  To get the public URL from Railway:")
        print("    1. Go to your Railway project")
        print("    2. Click on PostgreSQL service")
        print("    3. Go to 'Variables' or 'Connect' tab")
        print("    4. Copy the external/public connection URL")

    # Mask password for logging
    masked_url = mask_password(database_url)
    print(f"Loaded DATABASE_URL: {masked_url}")

    return database_url


def mask_password(url: str) -> str:
    """Mask password in database URL for safe logging."""
    try:
        # Format: postgresql://user:password@host:port/database
        if "@" in url and ":" in url:
            parts = url.split("@")
            auth_parts = parts[0].split(":")
            if len(auth_parts) >= 3:
                # Mask everything after the second colon (the password)
                protocol_user = ":".join(auth_parts[:2])
                return f"{protocol_user}:****@{parts[1]}"
    except Exception:
        pass
    return url[:30] + "..." if len(url) > 30 else url


def get_migration_path() -> Path:
    """Get the path to the migration SQL file."""
    project_root = get_project_root()
    migration_path = project_root / "migrations" / "001_initial_schema.sql"

    if not migration_path.exists():
        print(f"ERROR: Migration file not found at {migration_path}")
        sys.exit(1)

    return migration_path


def test_connection(database_url: str) -> bool:
    """Test database connection before running migration."""
    print("\n[1/5] Testing database connection...")
    try:
        conn = psycopg2.connect(database_url, connect_timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"  Connected to PostgreSQL: {version[:60]}...")
        cursor.close()
        conn.close()
        return True
    except psycopg2.OperationalError as e:
        print(f"  ERROR: Failed to connect to database")
        print(f"  Details: {str(e)}")
        print("\n  TROUBLESHOOTING:")
        print("  -" * 30)
        if "railway" in database_url.lower():
            print("  Railway PostgreSQL connection failed. Common causes:")
            print("  1. Public networking not enabled on Railway database")
            print("  2. Incorrect public hostname or port")
            print("  3. Database service not running")
            print("")
            print("  To get the correct public URL:")
            print("  1. Open Railway dashboard (https://railway.app)")
            print("  2. Select your project and PostgreSQL service")
            print("  3. Click 'Settings' or 'Connect' tab")
            print("  4. Enable 'Public Networking' if not enabled")
            print("  5. Copy the public DATABASE_URL")
            print("  6. Update DATABASE_URL_PUBLIC in .env file")
            print("")
            print("  The URL format should be:")
            print("  postgresql://postgres:PASSWORD@HOST.proxy.rlwy.net:PORT/railway")
        else:
            print("  Please verify:")
            print("  1. Database server is running")
            print("  2. Host, port, and credentials are correct")
            print("  3. Network allows connection to the database")
        return False
    except Exception as e:
        print(f"  ERROR: Unexpected error during connection test")
        print(f"  Details: {str(e)}")
        return False


def check_existing_tables(database_url: str) -> list:
    """Check for existing tables to determine if migration already ran."""
    print("\n[2/5] Checking existing database state...")
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)

        tables = [row[0] for row in cursor.fetchall()]

        if tables:
            print(f"  Found {len(tables)} existing tables: {', '.join(tables)}")
        else:
            print("  Database is empty (no existing tables)")

        cursor.close()
        conn.close()
        return tables
    except Exception as e:
        print(f"  WARNING: Could not check existing tables: {str(e)}")
        return []


def create_extensions(database_url: str) -> bool:
    """Create required extensions including PostGIS (requires separate transaction).

    Returns:
        bool: True if all extensions were created successfully
    """
    print("\n[3/5] Creating database extensions...")

    # All required extensions (PostGIS is now required - confirmed available on Railway)
    required_extensions = [
        ("uuid-ossp", "UUID generation functions"),
        ("pg_trgm", "Trigram matching for fuzzy search"),
        ("postgis", "Spatial and geographic objects (PostGIS 3.7)")
    ]

    try:
        # Extensions often need autocommit mode
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Create all required extensions
        for ext_name, ext_desc in required_extensions:
            try:
                cursor.execute(f'CREATE EXTENSION IF NOT EXISTS "{ext_name}";')
                print(f"  Extension '{ext_name}' ({ext_desc}): OK")
            except psycopg2.Error as e:
                if "already exists" in str(e).lower():
                    print(f"  Extension '{ext_name}' ({ext_desc}): Already exists")
                else:
                    print(f"  Extension '{ext_name}' ({ext_desc}): FAILED - {str(e)}")
                    cursor.close()
                    conn.close()
                    return False

        # Verify PostGIS version
        cursor.execute("SELECT PostGIS_Version();")
        postgis_version = cursor.fetchone()[0]
        print(f"  PostGIS version confirmed: {postgis_version}")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"  ERROR: Failed to create extensions: {str(e)}")
        return False


def run_migration(database_url: str, migration_path: Path) -> bool:
    """Execute the migration SQL file in a transaction.

    This migration uses full PostGIS features:
    - GEOMETRY(MultiPolygon, 4326) columns for spatial data
    - GIST indexes for spatial queries
    - PostGIS functions like ST_Centroid, ST_AsText
    """
    print("\n[4/5] Running database migration...")
    print(f"  Migration file: {migration_path.name}")
    print("  PostGIS mode: FULL (GEOMETRY columns + GIST indexes enabled)")

    # Read migration file
    try:
        with open(migration_path, "r", encoding="utf-8") as f:
            migration_sql = f.read()
        print(f"  Migration file size: {len(migration_sql):,} bytes")
    except Exception as e:
        print(f"  ERROR: Failed to read migration file: {str(e)}")
        return False

    # Remove extension creation (already handled separately)
    # This prevents errors if extensions are already created
    migration_sql_cleaned = migration_sql
    for ext in ["uuid-ossp", "postgis", "pg_trgm"]:
        migration_sql_cleaned = migration_sql_cleaned.replace(
            f'CREATE EXTENSION IF NOT EXISTS "{ext}";',
            f'-- Extension {ext} already created'
        )

    conn = None
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        start_time = datetime.now()

        # Execute migration in transaction
        cursor.execute(migration_sql_cleaned)

        # Commit if no errors
        conn.commit()

        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"  Migration completed successfully in {elapsed:.2f} seconds")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        print(f"  ERROR: Migration failed: {str(e)}")

        if conn:
            print("  Rolling back transaction...")
            conn.rollback()
            conn.close()

        return False

    except Exception as e:
        print(f"  ERROR: Unexpected error during migration: {str(e)}")

        if conn:
            print("  Rolling back transaction...")
            conn.rollback()
            conn.close()

        return False


def verify_migration(database_url: str) -> bool:
    """Verify that all expected tables were created."""
    print("\n[5/5] Verifying migration results...")

    expected_tables = [
        "properties",
        "property_history",
        "subdivisions",
        "assessment_analyses",
        "users",
        "user_properties",
        "schema_migrations"
    ]

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Check tables
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)

        actual_tables = [row[0] for row in cursor.fetchall()]

        print("\n  Tables created:")
        print("  " + "-" * 50)

        all_found = True
        for table in expected_tables:
            if table in actual_tables:
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                status = "OK"
                print(f"  {table:30} | {count:8} rows | {status}")
            else:
                status = "MISSING"
                all_found = False
                print(f"  {table:30} | {'N/A':>8} | {status}")

        print("  " + "-" * 50)

        # Check PostGIS extension (required)
        print("\n  Verifying PostGIS extension...")
        cursor.execute("SELECT PostGIS_Full_Version();")
        postgis_full = cursor.fetchone()[0]
        print(f"  PostGIS: {postgis_full[:80]}...")

        # Verify geometry column type on properties table
        print("\n  Verifying geometry column types...")
        cursor.execute("""
            SELECT column_name, udt_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'properties' AND column_name = 'geometry';
        """)
        geom_col = cursor.fetchone()
        if geom_col:
            col_name, udt_name, data_type = geom_col
            if udt_name == 'geometry':
                print(f"  properties.geometry: GEOMETRY type - OK (full PostGIS)")
            else:
                print(f"  properties.geometry: {udt_name} type - WARNING (expected GEOMETRY)")
                all_found = False
        else:
            print("  properties.geometry: NOT FOUND")
            all_found = False

        # Verify spatial index exists
        print("\n  Verifying spatial indexes...")
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'properties' AND indexname = 'idx_properties_geometry';
        """)
        spatial_idx = cursor.fetchone()
        if spatial_idx and 'gist' in spatial_idx[1].lower():
            print(f"  idx_properties_geometry: GIST index - OK")
        else:
            print(f"  idx_properties_geometry: NOT FOUND or not GIST")
            all_found = False

        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'subdivisions' AND indexname = 'idx_subdivisions_geometry';
        """)
        spatial_idx2 = cursor.fetchone()
        if spatial_idx2 and 'gist' in spatial_idx2[1].lower():
            print(f"  idx_subdivisions_geometry: GIST index - OK")
        else:
            print(f"  idx_subdivisions_geometry: NOT FOUND or not GIST")

        # Check for ENUM types
        print("\n  Verifying ENUM types...")
        cursor.execute("""
            SELECT typname
            FROM pg_type
            WHERE typtype = 'e'
            AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            ORDER BY typname;
        """)
        enum_types = [row[0] for row in cursor.fetchall()]

        expected_enums = [
            "user_type_enum",
            "ownership_type_enum",
            "recommendation_action_enum",
            "analysis_methodology_enum"
        ]

        for enum in expected_enums:
            status = "OK" if enum in enum_types else "MISSING"
            print(f"  {enum:35} | {status}")

        # Check views
        print("\n  Verifying views...")
        cursor.execute("""
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        views = [row[0] for row in cursor.fetchall()]

        expected_views = ["v_properties_full", "v_property_assessment_summary"]
        for view in expected_views:
            status = "OK" if view in views else "MISSING"
            print(f"  {view:35} | {status}")

        cursor.close()
        conn.close()

        return all_found

    except Exception as e:
        print(f"  ERROR: Failed to verify migration: {str(e)}")
        return False


def main():
    """Main entry point for migration script."""
    print("=" * 60)
    print("Taxdown Database Migration Script")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load configuration
    database_url = load_database_url()
    migration_path = get_migration_path()

    # Test connection
    if not test_connection(database_url):
        print("\nMIGRATION ABORTED: Database connection failed")
        sys.exit(1)

    # Check existing state
    existing_tables = check_existing_tables(database_url)

    # Check if migration already ran
    if "schema_migrations" in existing_tables:
        print("\n  WARNING: schema_migrations table exists.")
        print("  This may indicate the migration has already been executed.")
        # Continue anyway - the migration uses IF NOT EXISTS and ON CONFLICT

    # Create extensions first (some need autocommit)
    # PostGIS is now required - the new Railway database has PostGIS 3.7 support
    if not create_extensions(database_url):
        print("\nMIGRATION ABORTED: Failed to create required extensions (including PostGIS)")
        sys.exit(1)

    # Run migration with full PostGIS features
    if not run_migration(database_url, migration_path):
        print("\nMIGRATION FAILED: See errors above")
        sys.exit(1)

    # Verify results
    if not verify_migration(database_url):
        print("\nMIGRATION WARNING: Some expected objects are missing")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("MIGRATION COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
