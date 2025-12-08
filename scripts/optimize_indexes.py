"""
Add performance indexes to database.
"""

from sqlalchemy import create_engine, text
import os
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

INDEXES = [
    # Property search indexes
    "CREATE INDEX IF NOT EXISTS idx_properties_city ON properties(city)",
    "CREATE INDEX IF NOT EXISTS idx_properties_subdivision ON properties(subdivname)",
    "CREATE INDEX IF NOT EXISTS idx_properties_total_value ON properties(total_val_cents)",
    "CREATE INDEX IF NOT EXISTS idx_properties_assessed_value ON properties(assess_val_cents)",

    # Full text search
    "CREATE INDEX IF NOT EXISTS idx_properties_address_trgm ON properties USING gin(ph_add gin_trgm_ops)",

    # Analysis queries
    "CREATE INDEX IF NOT EXISTS idx_analysis_property_date ON assessment_analyses(property_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_analysis_fairness ON assessment_analyses(fairness_score)",

    # Portfolio queries
    "CREATE INDEX IF NOT EXISTS idx_portfolio_props_portfolio ON portfolio_properties(portfolio_id)",
    "CREATE INDEX IF NOT EXISTS idx_portfolio_props_property ON portfolio_properties(property_id)",
]

def create_indexes():
    with engine.connect() as conn:
        # Enable trigram extension for fuzzy search
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            conn.commit()
            print("[OK] pg_trgm extension enabled")
        except Exception as e:
            print(f"[!] pg_trgm extension - {e}")

        for idx_sql in INDEXES:
            try:
                conn.execute(text(idx_sql))
                conn.commit()
                print(f"[OK] {idx_sql[:60]}...")
            except Exception as e:
                print(f"[!] {idx_sql[:60]}... - {e}")

    print("\nIndex optimization complete!")

if __name__ == "__main__":
    create_indexes()
