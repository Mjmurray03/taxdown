"""
Test database connection and basic queries.
Run this to verify your setup is working correctly.
"""
import os
import sys
from dotenv import load_dotenv


def main():
    # Load environment variables
    load_dotenv()

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not found in .env file")
        print("   Copy .env.example to .env and add your database URL")
        sys.exit(1)

    print("Testing database connection...")

    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        # Test 1: Check tables exist and get row counts
        print("\n[TABLE ROW COUNTS]")

        cur.execute("SELECT COUNT(*) FROM properties")
        prop_count = cur.fetchone()[0]
        print(f"   properties: {prop_count:,} records")

        cur.execute("SELECT COUNT(*) FROM subdivisions")
        sub_count = cur.fetchone()[0]
        print(f"   subdivisions: {sub_count:,} records")

        # Test 2: Verify PostGIS is available
        print("\n[POSTGIS CHECK]")
        cur.execute("SELECT PostGIS_Version()")
        postgis_version = cur.fetchone()[0]
        print(f"   PostGIS version: {postgis_version}")

        # Test 3: Run a simple spatial query
        print("\n[SAMPLE SPATIAL QUERY]")
        cur.execute("""
            SELECT address, city,
                   ST_X(geometry) as longitude,
                   ST_Y(geometry) as latitude
            FROM properties
            WHERE geometry IS NOT NULL
            LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            print(f"   Sample property: {row[0]}, {row[1]}")
            print(f"   Coordinates: ({row[2]:.4f}, {row[3]:.4f})")

        # Test 4: Check for NULL parcel_ids
        print("\n[NULL PARCEL_ID CHECK]")
        cur.execute("SELECT COUNT(*) FROM properties WHERE parcel_id IS NULL")
        null_count = cur.fetchone()[0]
        print(f"   Properties with NULL parcel_id: {null_count:,} records")

        # Test 5: Sample monetary value
        print("\n[MONETARY VALUE CHECK]")
        cur.execute("""
            SELECT address, market_value, market_value/100.0 as market_value_dollars
            FROM properties
            WHERE market_value IS NOT NULL AND market_value > 0
            LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            print(f"   Address: {row[0]}")
            print(f"   Market value (cents): {row[1]}")
            print(f"   Market value (dollars): ${row[2]:,.2f}")

        cur.close()
        conn.close()

        print("\n[SUCCESS] Database connection working correctly!")
        return 0

    except ImportError as e:
        print(f"ERROR: Missing dependency - {e}")
        print("   Run: pip install -r requirements.txt")
        return 1

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
