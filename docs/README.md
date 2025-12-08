# Taxdown Documentation Index

## Quick Navigation

### Getting Started (New Team Members)

Start here if you're new to the project:

1. **[docs/quick_reference.md](quick_reference.md)** - 3 minute overview
   - One-page quick reference card
   - Essential commands and queries
   - Common issues and fixes
   - Python connection template

2. **[docs/database_access.md](database_access.md)** - 5 minute quick start
   - Setup steps for all platforms
   - Database overview
   - Key columns reference
   - Common queries with examples
   - Troubleshooting

3. **[docs/team_onboarding.md](team_onboarding.md)** - 30 minute complete guide
   - Step-by-step setup (5 minutes to ready)
   - Complete schema documentation
   - 6+ common tasks with code examples
   - Development workflow
   - Security best practices
   - Full troubleshooting guide
   - Success criteria checklist

### Advanced Reference

After getting started, use these for deep dives:

- **[docs/schema_design.md](schema_design.md)** - Complete schema reference
  - Detailed table structures
  - Column documentation
  - Relationships and constraints
  - Indexes and performance

- **[docs/query_design.md](query_design.md)** - Query patterns and best practices
  - Common query patterns
  - Spatial queries
  - Performance optimization
  - Example queries

- **[docs/column_mapping.md](column_mapping.md)** - Data mapping reference
  - Column meanings
  - Data types and ranges
  - NULL handling
  - Value transformations

## Setup & Testing

### Test Your Setup

Run this to verify everything is working:
```bash
python src/utils/test_connection.py
```

This tests:
- Database connection
- Table existence and row counts
- PostGIS availability
- Spatial query capability
- NULL value handling
- Monetary value format

### Configuration Files

- **[.env.example](.env.example)** - Template for .env file
  - Get DATABASE_URL from MJ
  - Copy to .env (never commit)
  - Contains all connection information

- **[requirements.txt](requirements.txt)** - Python dependencies
  - psycopg2-binary (PostgreSQL driver)
  - geopandas (spatial data)
  - pandas (data manipulation)
  - SQLAlchemy (ORM)
  - python-dotenv (environment variables)
  - shapely (geometry operations)
  - pyarrow (data serialization)

## Project Structure

```
/c/taxdown/
  docs/
    README.md                    <- You are here
    quick_reference.md           <- Start here (3 min)
    database_access.md           <- Quick start (5 min)
    team_onboarding.md           <- Full guide (30 min)
    schema_design.md             <- Advanced reference
    query_design.md              <- Query patterns
    column_mapping.md            <- Data mapping

  src/
    utils/
      test_connection.py         <- Test your setup
      __init__.py
    etl/
      load_properties.py         <- Load property data
      load_subdivisions.py       <- Load subdivision data
      run_migration.py           <- Run database migrations

  requirements.txt               <- Python dependencies
  .env.example                   <- Config template
  .gitignore                     <- Ignores .env
```

## Database Overview

### Properties Table
- **173,743** property records across Arkansas
- Street address, city, ZIP
- Property owner name
- Market, appraised, taxable values (all in CENTS)
- Geographic coordinates (WGS84)
- Subdivision assignment (optional)
- ~2,697 records missing parcel IDs

### Subdivisions Table
- **4,041** subdivision boundaries
- Subdivision name
- Polygon geometry (WGS84)
- Contains properties via FK relationship

## Critical Information

### Monetary Values
All monetary columns store values in **CENTS**, not dollars:
```sql
-- Wrong: will search for cents value
WHERE market_value > 500000

-- Right: 5000000 cents = $50,000
WHERE market_value > 5000000

-- Display as dollars:
SELECT market_value/100.0 as value_dollars
```

### Geometry Coordinates
All geometry uses **WGS84 (EPSG:4326)** - standard latitude/longitude:
```sql
-- Extract coordinates
SELECT ST_X(geometry) as longitude,
       ST_Y(geometry) as latitude
FROM properties

-- Spatial query (1km radius)
WHERE ST_DWithin(geometry::geography,
                 ST_SetSRID(ST_MakePoint(-97.5, 30.3), 4326)::geography,
                 1000)
```

### NULL Parcel IDs
~2,697 properties don't have parcel IDs. Use UUID `id` as primary key:
```sql
-- This works (most reliable)
WHERE id = 'uuid-value'

-- This might return NULL
WHERE parcel_id = 'value'
```

## Common Tasks

### Look up a property
See: [team_onboarding.md - Task: Find a Property by Address](team_onboarding.md#task-find-a-property-by-address)

### Find properties in subdivision
See: [quick_reference.md - Properties in a subdivision](quick_reference.md#properties-in-a-subdivision)

### Get owner's portfolio
See: [quick_reference.md - Owner portfolio](quick_reference.md#owner-portfolio)

### Spatial proximity search
See: [database_access.md - Spatial query](database_access.md#spatial-query---properties-near-a-point)

### Bulk data analysis
See: [team_onboarding.md - Using Pandas for Analysis](team_onboarding.md#using-pandas-for-analysis)

## Troubleshooting

### Quick fixes
See: [quick_reference.md - Common Issues](quick_reference.md#common-issues)

### Detailed troubleshooting
See: [team_onboarding.md - Troubleshooting](team_onboarding.md#7-troubleshooting)

### Connection not working?
1. Verify DATABASE_URL in .env file
2. Run `python src/utils/test_connection.py`
3. Check Railway status at railway.app
4. Contact MJ if credentials need refresh

## Security

### Never commit .env
- `.env` is in `.gitignore` for protection
- Contains DATABASE_URL with credentials
- Get DATABASE_URL from MJ (not email)
- Store only locally in `.env`

### Security best practices
See: [team_onboarding.md - Security & Best Practices](team_onboarding.md#8-security--best-practices)

## Support & Contact

### For database access
Contact: **MJ**
- Request: DATABASE_URL
- Never send via email unencrypted
- Store in .env file (never commit)

### For technical guidance
- Check relevant docs above
- Run `python src/utils/test_connection.py` for diagnostics
- Review code examples before writing queries
- Check existing scripts in `src/etl/`

### For schema questions
See: [docs/schema_design.md](schema_design.md)

### For query help
See: [docs/query_design.md](query_design.md)

## Learning Path

### Day 1 (Getting Started)
1. Read [quick_reference.md](quick_reference.md) (3 min)
2. Follow [database_access.md](database_access.md) setup (5 min)
3. Run `python src/utils/test_connection.py` (1 min)
4. Try one query from quick_reference.md (5 min)

### Day 2 (Complete Onboarding)
1. Read [team_onboarding.md](team_onboarding.md) (30 min)
2. Try code examples from the guide (30 min)
3. Run your first analysis script (30 min)

### Ongoing (Development)
1. Reference [schema_design.md](schema_design.md) for column details
2. Reference [query_design.md](query_design.md) for patterns
3. Refer to [column_mapping.md](column_mapping.md) for data meanings

## Documentation Files

### Core Documentation (These Files)
- **[quick_reference.md](quick_reference.md)** - 164 lines, 1-page card
- **[database_access.md](database_access.md)** - 84 lines, quick start
- **[team_onboarding.md](team_onboarding.md)** - 513 lines, complete guide
- **[schema_design.md](schema_design.md)** - Existing schema reference
- **[query_design.md](query_design.md)** - Existing query patterns
- **[column_mapping.md](column_mapping.md)** - Existing column reference

### Summary Documents (Root Level)
- **[TEAM_ACCESS_SETUP.md](../TEAM_ACCESS_SETUP.md)** - Setup summary
- **[DELIVERABLES_SUMMARY.txt](../DELIVERABLES_SUMMARY.txt)** - Deliverables list

### Utilities
- **[src/utils/test_connection.py](../src/utils/test_connection.py)** - 96 lines, connection test

## Quick Command Reference

```bash
# Setup (first time)
git clone <repo-url>
cd taxdown
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env with DATABASE_URL from MJ
python src/utils/test_connection.py

# Activate environment (each session)
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Run analysis
python scripts/your_script.py

# Update dependencies
pip freeze > requirements.txt
```

## Start Here

**First time?** Read in this order:
1. This file (you're reading it)
2. [quick_reference.md](quick_reference.md) - 3 minutes
3. [database_access.md](database_access.md) - 5 minutes
4. Run `python src/utils/test_connection.py`
5. Try a query from [quick_reference.md](quick_reference.md)

**Need detailed guide?** Read:
- [team_onboarding.md](team_onboarding.md) - Complete 30 minute walkthrough

**Advanced work?** Reference:
- [schema_design.md](schema_design.md) - Detailed schema
- [query_design.md](query_design.md) - Query patterns
- [column_mapping.md](column_mapping.md) - Data reference

---

**Last Updated**: December 8, 2024
**Status**: Complete and Ready for Team Use
**Next Steps**: Read quick_reference.md (3 minutes)
