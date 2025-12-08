# Taxdown Team Database Onboarding Guide

## Overview

This document provides everything you need to access and work with the Taxdown PostgreSQL database on Railway. The database contains property assessment data with geospatial capabilities.

### What You'll Have Access To
- 173,743 property records across Arkansas
- 4,041 subdivision boundaries with geometry
- Full geospatial query capabilities (PostGIS)
- ETL pipeline for data ingestion and updates

---

## 1. Initial Setup (First Time Only)

### Step 1: Clone Repository
```bash
git clone <repository-url>
cd taxdown
```

### Step 2: Create Python Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

This installs:
- `psycopg2-binary` - PostgreSQL database driver
- `geopandas` - Geospatial data operations
- `pandas` - Data manipulation
- `SQLAlchemy` - Database ORM
- `python-dotenv` - Environment variable management
- `shapely` - Geometry operations
- `pyarrow` - Efficient data serialization

### Step 4: Configure Database Access
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your DATABASE_URL
# Ask MJ for the DATABASE_URL - it's a PostgreSQL connection string
nano .env  # or use your favorite editor
```

Your `.env` file should look like:
```
DATABASE_URL=postgresql://username:password@host:port/database
```

**IMPORTANT**: Never commit your `.env` file! It's already in `.gitignore` to prevent accidental commits.

### Step 5: Test Your Connection
```bash
python src/utils/test_connection.py
```

Expected output:
```
Testing database connection...

[TABLE ROW COUNTS]
   properties: 173,743 records
   subdivisions: 4,041 records

[POSTGIS CHECK]
   PostGIS version: 3.x.x

[SAMPLE SPATIAL QUERY]
   Sample property: 123 Main Street, Bentonville
   Coordinates: (-94.7289, 36.3728)

[NULL PARCEL_ID CHECK]
   Properties with NULL parcel_id: 2,697 records

[MONETARY VALUE CHECK]
   Address: 123 Main Street
   Market value (cents): 50000000
   Market value (dollars): $500,000.00

[SUCCESS] Database connection working correctly!
```

---

## 2. Database Schema

### Properties Table (`properties`)

**Purpose**: Core property records with assessment data and location geometry

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key, always unique |
| `parcel_id` | text | County parcel ID (NULL for ~2,697 records) |
| `address` | text | Street address |
| `city` | text | City name |
| `zip` | text | ZIP code |
| `owner_name` | text | Property owner name |
| `market_value` | bigint | In CENTS (divide by 100 for dollars) |
| `appraised_value` | bigint | In CENTS |
| `taxable_value` | bigint | In CENTS |
| `geometry` | geometry | PostGIS point (WGS84/EPSG:4326) |
| `subdivision_id` | UUID | Foreign key to subdivisions |
| `created_at` | timestamp | Record creation time |
| `updated_at` | timestamp | Last modification time |

### Subdivisions Table (`subdivisions`)

**Purpose**: Subdivision boundaries with names and geometry

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `name` | text | Subdivision name |
| `geometry` | geometry | Polygon boundary (WGS84/EPSG:4326) |
| `created_at` | timestamp | Record creation time |
| `updated_at` | timestamp | Last modification time |

---

## 3. Common Tasks & Queries

### Task: Find a Property by Address

```python
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Search for properties matching an address
cur.execute("""
    SELECT id, address, city, owner_name, market_value/100.0 as value_dollars
    FROM properties
    WHERE address ILIKE %s
    ORDER BY address
""", ('%Main Street%',))

for row in cur.fetchall():
    print(f"{row[1]}, {row[2]} - {row[3]} (${row[4]:,.2f})")

cur.close()
conn.close()
```

### Task: Find Properties in a Subdivision

```sql
SELECT p.id, p.address, p.owner_name, p.market_value/100.0 as value
FROM properties p
JOIN subdivisions s ON p.subdivision_id = s.id
WHERE s.name ILIKE '%oak%'
ORDER BY p.market_value DESC;
```

### Task: Get Owner's Property Portfolio

```sql
SELECT address, city, market_value/100.0 as value, appraised_value/100.0 as appraised
FROM properties
WHERE owner_name ILIKE '%smith%'
ORDER BY market_value DESC;
```

### Task: Spatial Query - Properties Near a Location

```sql
-- Find properties within 1km of coordinates (-97.5, 30.3)
SELECT address, owner_name,
       ST_Distance(geometry::geography,
                   ST_SetSRID(ST_MakePoint(-97.5, 30.3), 4326)::geography) as distance_meters
FROM properties
WHERE ST_DWithin(geometry::geography,
                 ST_SetSRID(ST_MakePoint(-97.5, 30.3), 4326)::geography,
                 1000)
ORDER BY distance_meters;
```

### Task: Get Statistics on Properties

```sql
-- Basic statistics
SELECT
    COUNT(*) as total_properties,
    COUNT(DISTINCT owner_name) as unique_owners,
    COUNT(CASE WHEN parcel_id IS NULL THEN 1 END) as missing_parcel_ids,
    MIN(market_value)/100.0 as min_value,
    AVG(market_value)/100.0 as avg_value,
    MAX(market_value)/100.0 as max_value,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY market_value)/100.0 as median_value
FROM properties;
```

---

## 4. Important Data Characteristics

### Monetary Values: Always in CENTS

All monetary columns store values in cents to avoid floating-point precision issues.

```python
# WRONG - will give incorrect results
SELECT market_value FROM properties WHERE market_value > 500000

# RIGHT - convert to dollars first
SELECT market_value/100.0 as value_dollars FROM properties WHERE market_value > 5000000
```

### Geometry: WGS84 (EPSG:4326)

All geometry is stored in WGS84 latitude/longitude coordinates.

```sql
-- Check geometry validity
SELECT COUNT(*) FROM properties WHERE geometry IS NULL;

-- Extract coordinates
SELECT ST_X(geometry) as longitude, ST_Y(geometry) as latitude FROM properties LIMIT 1;
```

### Parcel IDs: May Be NULL

~2,697 properties (~1.5%) don't have parcel IDs. Always use the UUID `id` as primary identifier.

```sql
-- Find properties without parcel IDs
SELECT COUNT(*) FROM properties WHERE parcel_id IS NULL;
```

### Subdivision Relationships

Not all properties are assigned to subdivisions.

```sql
-- Check subdivision coverage
SELECT COUNT(*) as no_subdivision FROM properties WHERE subdivision_id IS NULL;
SELECT COUNT(*) as with_subdivision FROM properties WHERE subdivision_id IS NOT NULL;
```

---

## 5. ETL Scripts Location

### Main Scripts
- `src/etl/load_properties.py` - Load/update property records
- `src/etl/load_subdivisions.py` - Load/update subdivision boundaries
- `src/etl/run_migration.py` - Run database migrations

### Running ETL
```bash
# Activate virtual environment first
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Run property load
python src/etl/load_properties.py

# Run subdivision load
python src/etl/load_subdivisions.py

# Check logs
tail -f load_final.log
```

---

## 6. Development Workflow

### Creating a New Analysis Script

1. Create a file in the `scripts/` directory
2. Use this template:

```python
"""
Brief description of what this script does.
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2
import pandas as pd

load_dotenv()

def main():
    try:
        # Connect to database
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))

        # Use pandas for easier data handling
        query = """
            SELECT id, address, market_value/100.0 as value
            FROM properties
            WHERE city = %s
        """

        df = pd.read_sql(query, conn, params=('Bentonville',))
        print(f"Found {len(df)} properties")
        print(df.head())

        conn.close()
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

3. Run your script:
```bash
python scripts/your_script.py
```

### Using Pandas for Analysis

```python
import pandas as pd
import psycopg2

conn = psycopg2.connect(os.getenv('DATABASE_URL'))

# Read entire table
df = pd.read_sql("SELECT * FROM properties LIMIT 10000", conn)

# Basic analysis
print(df.describe())
print(df['city'].value_counts())

conn.close()
```

---

## 7. Troubleshooting

### "Connection refused" Error
**Problem**: Cannot connect to database
**Solution**:
1. Verify DATABASE_URL in .env file
2. Check Railway status at railway.app
3. Ensure you're on a network with Railway access (no restrictive firewall)

### "ModuleNotFoundError: No module named 'psycopg2'"
**Problem**: Missing dependencies
**Solution**:
```bash
pip install -r requirements.txt
```

### "SSL CERTIFICATE_VERIFY_FAILED"
**Problem**: SSL certificate verification failure
**Solution**: Railway uses SSL by default. This should work automatically. If you get this error:
1. Check your DATABASE_URL includes `sslmode=require`
2. Update psycopg2: `pip install --upgrade psycopg2-binary`

### "FATAL: no pg_hba.conf entry"
**Problem**: Authentication failure
**Solution**:
1. Double-check DATABASE_URL credentials
2. Get fresh DATABASE_URL from MJ
3. Ensure no typos (especially password special characters)

### "Geometry is NULL" Error
**Problem**: PostGIS geometry column has NULL values
**Solution**: Always check for NULL geometries:
```sql
SELECT * FROM properties WHERE geometry IS NULL;
```

---

## 8. Security & Best Practices

### Environment Variables
```bash
# GOOD - uses environment variables
password = os.getenv('DATABASE_URL')
conn = psycopg2.connect(password)

# BAD - hardcoded credentials
conn = psycopg2.connect('postgresql://user:pass@host/db')
```

### Connection Pooling (For Production)
```python
# For long-running applications, use connection pooling
from sqlalchemy import create_engine

engine = create_engine(
    os.getenv('DATABASE_URL'),
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600
)
```

### Query Parameterization (Prevents SQL Injection)
```python
# SAFE - parameterized query
cur.execute("SELECT * FROM properties WHERE city = %s", ('Bentonville',))

# UNSAFE - string interpolation
cur.execute(f"SELECT * FROM properties WHERE city = '{city}'")
```

### Commit Strategy
```bash
# Never commit .env
git status  # Should show .env not in staging area

# Commit only code changes
git add src/ docs/ requirements.txt
git commit -m "Add new analysis script"
```

---

## 9. Contact & Support

### Getting Help
- **Database Access**: Contact MJ for DATABASE_URL
- **Schema Questions**: See docs/schema_design.md
- **ETL Issues**: Check src/etl/ directory for scripts
- **General Questions**: Check existing documentation in docs/

### Resources
- PostGIS Documentation: https://postgis.net/documentation/
- psycopg2 Docs: https://www.psycopg.org/psycopg2/docs/
- GeoPandas: https://geopandas.org/
- Railway Docs: https://docs.railway.app/

---

## 10. Quick Reference

### Connection Test
```bash
python src/utils/test_connection.py
```

### Common Commands
```bash
# Activate environment
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Install packages
pip install -r requirements.txt

# Run analysis script
python scripts/my_script.py

# Update environment
pip freeze > requirements.txt
```

### File Structure
```
taxdown/
  .env                      # Your credentials (NOT in git)
  .env.example             # Example template
  requirements.txt         # Python dependencies
  docs/
    database_access.md     # This file
    schema_design.md       # Detailed schema
    query_design.md        # Query patterns
  src/
    etl/                   # Data loading scripts
      load_properties.py
      load_subdivisions.py
    utils/
      test_connection.py   # Connection test
  scripts/                 # Your analysis scripts
```

---

## Checklist: You're Ready When...

- [ ] Virtual environment created and activated
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] `.env` file created with valid DATABASE_URL
- [ ] Connection test passed: `python src/utils/test_connection.py`
- [ ] Can query properties table
- [ ] Can query subdivisions table
- [ ] PostGIS version shown in test output
- [ ] Understand that monetary values are in CENTS
- [ ] Understand geometry is in WGS84 (EPSG:4326)

---

**Last Updated**: December 8, 2024
