# Taxdown Database Quick Reference

## Setup (First Time)
```bash
# 1. Clone and setup
git clone <repo-url>
cd taxdown

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure database
cp .env.example .env
# Edit .env and add DATABASE_URL from MJ

# 5. Test connection
python src/utils/test_connection.py
```

## Connection
```python
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
# Your query here
cur.close()
conn.close()
```

## Data Overview
- **Properties**: 173,743 records with coordinates and assessment values
- **Subdivisions**: 4,041 boundaries
- **Geometry**: WGS84 (EPSG:4326) - lat/lon
- **Monetary values**: All in CENTS (divide by 100 for dollars)
- **Missing data**: ~2,697 properties have NULL parcel_id

## Essential Queries

### Find property by address
```sql
SELECT * FROM properties
WHERE address ILIKE '%123 Main%'
LIMIT 10;
```

### Properties in a subdivision
```sql
SELECT p.address, p.owner_name, p.market_value/100.0
FROM properties p
JOIN subdivisions s ON p.subdivision_id = s.id
WHERE s.name ILIKE '%oak%';
```

### Owner portfolio
```sql
SELECT address, city, market_value/100.0 as value
FROM properties
WHERE owner_name ILIKE '%smith%'
ORDER BY market_value DESC;
```

### Statistics
```sql
SELECT
    COUNT(*) total,
    AVG(market_value)/100.0 avg_value,
    MAX(market_value)/100.0 max_value
FROM properties;
```

### Spatial query (near location)
```sql
SELECT address, owner_name,
  ST_Distance(geometry::geography,
    ST_SetSRID(ST_MakePoint(-97.5, 30.3), 4326)::geography) dist_meters
FROM properties
WHERE ST_DWithin(geometry::geography,
  ST_SetSRID(ST_MakePoint(-97.5, 30.3), 4326)::geography, 1000)
ORDER BY dist_meters;
```

## Key Columns Reference

### Properties Table
| Column | Type | Example |
|--------|------|---------|
| `id` | UUID | Primary key - use when parcel_id is NULL |
| `parcel_id` | text | County ID (may be NULL) |
| `address` | text | "123 Main Street" |
| `city` | text | "Bentonville" |
| `zip` | text | "72712" |
| `owner_name` | text | Property owner |
| `market_value` | bigint | In CENTS: 50000000 = $500,000 |
| `appraised_value` | bigint | In CENTS |
| `taxable_value` | bigint | In CENTS |
| `geometry` | geometry | Point (lon, lat) |
| `subdivision_id` | UUID | FK to subdivisions |

### Subdivisions Table
| Column | Type |
|--------|------|
| `id` | UUID |
| `name` | text |
| `geometry` | geometry |

## Python Template
```python
import os
import psycopg2
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))

# Use pandas for easier analysis
df = pd.read_sql("""
    SELECT address, city, market_value/100.0 as value
    FROM properties
    WHERE city = %s
    LIMIT 100
""", conn, params=('Bentonville',))

print(df.describe())
conn.close()
```

## Common Issues
| Issue | Fix |
|-------|-----|
| Connection refused | Check DATABASE_URL in .env |
| No module named psycopg2 | `pip install -r requirements.txt` |
| SSL certificate error | Railway uses SSL by default, should work |
| Invalid monetary value | Divide by 100: `market_value/100.0` |
| NULL coordinates | Filter: `WHERE geometry IS NOT NULL` |

## Important Notes
- **ALWAYS divide monetary values by 100** to get dollars
- **Coordinates are WGS84** (standard lat/lon)
- **Use UUID `id` as primary key**, not parcel_id
- **Never commit .env** - it's in .gitignore
- **Ask MJ for DATABASE_URL** - contains credentials

## Files
- `docs/database_access.md` - Quick start guide
- `docs/team_onboarding.md` - Full onboarding guide
- `src/utils/test_connection.py` - Test your connection
- `.env.example` - Template for .env
- `requirements.txt` - Python dependencies

## Next Steps
1. Run `python src/utils/test_connection.py` to verify setup
2. Try a simple query from the examples above
3. Read `docs/team_onboarding.md` for detailed guidance
4. Check `docs/schema_design.md` for complete schema info
