"""
Data validation script for Taxdown database.
"""

import os
from sqlalchemy import create_engine, text
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL_PUBLIC",
    os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/taxdown")
)

# Fix postgres:// vs postgresql:// for SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

def run_validation():
    issues = defaultdict(list)

    with engine.connect() as conn:
        # Check 1: Properties with missing required fields
        result = conn.execute(text("""
            SELECT COUNT(*) FROM properties
            WHERE parcel_id IS NULL OR parcel_id = ''
        """))
        count = result.scalar()
        if count > 0:
            issues["missing_parcel_id"].append(f"{count} properties without parcel_id")

        # Check 2: Properties with invalid values
        result = conn.execute(text("""
            SELECT COUNT(*) FROM properties
            WHERE total_val_cents < 0 OR assess_val_cents < 0
        """))
        count = result.scalar()
        if count > 0:
            issues["negative_values"].append(f"{count} properties with negative values")

        # Check 3: Duplicate parcel IDs
        result = conn.execute(text("""
            SELECT parcel_id, COUNT(*) as cnt
            FROM properties
            GROUP BY parcel_id
            HAVING COUNT(*) > 1
        """))
        dupes = result.fetchall()
        if dupes:
            issues["duplicate_parcels"].append(f"{len(dupes)} duplicate parcel IDs")

        # Check 4: Properties with assessment ratio > 100%
        result = conn.execute(text("""
            SELECT COUNT(*) FROM properties
            WHERE total_val_cents > 0
            AND assess_val_cents > total_val_cents
        """))
        count = result.scalar()
        if count > 0:
            issues["high_assessment_ratio"].append(f"{count} properties with assessment > market value")

        # Check 5: Orphaned analysis results
        result = conn.execute(text("""
            SELECT COUNT(*) FROM assessment_analyses ar
            LEFT JOIN properties p ON ar.property_id = p.id
            WHERE p.id IS NULL
        """))
        count = result.scalar()
        if count > 0:
            issues["orphaned_analyses"].append(f"{count} analysis results without properties")

        # Summary stats
        total_properties = conn.execute(text("SELECT COUNT(*) FROM properties")).scalar()
        total_analyses = conn.execute(text("SELECT COUNT(*) FROM assessment_analyses")).scalar()
        total_subdivisions = conn.execute(text("SELECT COUNT(*) FROM subdivisions")).scalar()

        print("\n" + "="*50)
        print("TAXDOWN DATA VALIDATION REPORT")
        print("="*50)
        print(f"\nTotal Properties: {total_properties:,}")
        print(f"Total Analyses: {total_analyses:,}")
        print(f"Total Subdivisions: {total_subdivisions:,}")

        if issues:
            print("\n[!] ISSUES FOUND:")
            for category, messages in issues.items():
                print(f"\n  {category}:")
                for msg in messages:
                    print(f"    - {msg}")
        else:
            print("\n[OK] No issues found!")

        print("\n" + "="*50)

if __name__ == "__main__":
    run_validation()
