# Taxdown Database Access Guide

## Quick Start for Team Members

### Prerequisites
- Python 3.11+
- Git
- Text editor or IDE

### Setup Steps
1. Clone the repository
2. Create virtual environment: `python -m venv venv`
3. Activate: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env`
6. Get DATABASE_URL from MJ (do not commit this!)
7. Test connection: `python src/utils/test_connection.py`

### Database Overview
- **Host**: Railway PostgreSQL with PostGIS
- **Tables**:
  - `properties` (173,743 records)
  - `subdivisions` (4,041 records)

### Key Columns Reference

#### Properties Table
- `id` (UUID) - Primary key, always unique
- `parcel_id` (text) - County parcel ID (may be NULL for ~2,697 records)
- `address`, `city`, `zip` - Location info
- `owner_name` - Property owner
- `market_value`, `appraised_value`, `taxable_value` - **Values in CENTS**
- `geometry` - PostGIS geometry (WGS84/EPSG:4326)
- `subdivision_id` - Foreign key to subdivisions

#### Subdivisions Table
- `id` (UUID) - Primary key
- `name` - Subdivision name
- `geometry` - Boundary polygon

### Common Queries

#### Look up property by address
```sql
SELECT id, address, city, owner_name, market_value/100.0 as market_value_dollars
FROM properties
WHERE address ILIKE '%123 Main%';
```

#### Find properties in a subdivision
```sql
SELECT p.address, p.owner_name, p.market_value/100.0 as value
FROM properties p
JOIN subdivisions s ON p.subdivision_id = s.id
WHERE s.name ILIKE '%oak%';
```

#### Get owner's portfolio
```sql
SELECT address, city, market_value/100.0 as value
FROM properties
WHERE owner_name ILIKE '%smith%'
ORDER BY market_value DESC;
```

#### Spatial query - properties near a point
```sql
SELECT address, owner_name,
       ST_Distance(geometry::geography, ST_SetSRID(ST_MakePoint(-97.5, 30.3), 4326)::geography) as distance_meters
FROM properties
WHERE ST_DWithin(geometry::geography, ST_SetSRID(ST_MakePoint(-97.5, 30.3), 4326)::geography, 1000)
ORDER BY distance_meters;
```

### Important Notes
- **All monetary values are in CENTS** (divide by 100 for dollars)
- **Geometry is WGS84 (EPSG:4326)**
- **parcel_id may be NULL** for ~2,697 records (use UUID `id` instead)
- **Never commit .env** - DATABASE_URL contains credentials

### Troubleshooting
- **Connection refused**: Check if DATABASE_URL is correct
- **SSL error**: Railway requires SSL, should work by default
- **Import error**: Run `pip install -r requirements.txt`
