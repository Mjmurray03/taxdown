# Invalid Geometries - Reference List

**Total Invalid:** 66 out of 173,743 (0.04%)
**Date:** 2025-12-08

## Breakdown

| Category | Count |
|----------|-------|
| **Invalid with NULL parcel_id** | 27 (40.9% of invalid) |
| **Invalid with valid parcel_id** | 39 (59.1% of invalid) |
| **Total Invalid** | 66 (0.04% of all properties) |

## Properties with Invalid Geometries (With Parcel IDs)

| Parcel ID | Address | Subdivision | Geometry Type |
|-----------|---------|-------------|---------------|
| 01-05263-000 | 2000 NE MEMORIAL PARK SQ | BAKER'S PARK ADD-BENTONVILLE | ST_MultiPolygon |
| 06-00006-033 | E CENTERTON BLVD | 03-19-31-CENTERTON | ST_MultiPolygon |
| 15-03000-000 | | FOREST PARK-RURBAN | ST_MultiPolygon |
| 15-03006-000 | | FOREST PARK-RURBAN | ST_MultiPolygon |
| 15-09219-003 | ROBINSON RD | ROBINSON ORIG-RURBAN | ST_MultiPolygon |
| 16-15225-001 | | HILLSWICK SUB-BVV | ST_MultiPolygon |
| 16-15373-001 | | HOPEMAN SUB-BVV | ST_MultiPolygon |
| 16-28718-001 | | SIDLAW HILLS-BVV | ST_MultiPolygon |
| 16-34419-001 | | TOWNHOUSE TCT 3 A/K/A DRAKE CT-BVV | ST_MultiPolygon |
| 16-34488-000 | | TOWNHOUSE TCT 3 A/K/A DRAKE CT-BVV | ST_MultiPolygon |
| 16-34522-000 | NANTUCKET DR | TOWNHOUSE TCT 3 A/K/A DRAKE CT-BVV | ST_MultiPolygon |
| 16-34592-000 | 2 CORA CIR | BASILDON COURTS-BVV | ST_MultiPolygon |
| 16-34617-000 | 2 CORA CIR | BASILDON COURTS-BVV | ST_MultiPolygon |
| 16-34850-000 | | KINGSDALE COURTS-BVV | ST_MultiPolygon |
| 16-34942-000 | | MELANIE COURTS-BVV | ST_MultiPolygon |
| 16-34956-000 | JADE LN | MELANIE COURTS-BVV | ST_MultiPolygon |
| 16-39814-000 | | OAK KNOLL SUB-BVV | ST_MultiPolygon |
| 16-40013-001 | | KIPLING COURTS-BVV | ST_MultiPolygon |
| 16-40019-000 | NORWOOD DR | NORWOOD COURTS-BVV | ST_MultiPolygon |
| 16-40619-000 | | WINDSOR COURTS-BVV | ST_MultiPolygon |
| 16-40778-000 | | KIPLING COURTS-BVV | ST_MultiPolygon |
| 16-41044-002 | W LANCASHIRE BLVD | HIGHLAND PARK VILLAS-BVV | ST_MultiPolygon |
| 16-70222-000 | OFF LANCASHIRE | 22-21-31-BELLA VISTA | ST_MultiPolygon |
| 16-70247-001 | OFF PINION DR | 26-21-31-BELLA VISTA | ST_MultiPolygon |
| 16-79408-064 | BELLA VISTA WAY | 12-20-31-BELLA VISTA | ST_MultiPolygon |
| 18-00536-455 | 14097 THE PINES RD | 18-18-28-RURAL | ST_MultiPolygon |
| 18-00935-000 | | 16-19-28-RURAL | ST_MultiPolygon |
| 18-02441-000 | 13180 FRISCO CHURCH RD | 08-18-29-RURAL | ST_MultiPolygon |
| 18-04226-000 | 15424 US 62 HWY | 02-20-29-RURAL | ST_MultiPolygon |
| 18-04681-001 | 123 W TUCKS CHAPEL RD | 18-20-29-RURAL | ST_MultiPolygon |
| 18-05129-000 | 9781 BURNETT RD | 32-20-29-RURAL | ST_MultiPolygon |
| 18-05319-000 | WENDELL JONES RD | 15-21-29-RURAL | ST_MultiPolygon |
| 18-10370-006 | OLD HWY 68 | 03-17-32-RURAL | ST_MultiPolygon |
| 18-11115-000 | 15614 OSAGE HILL RD | 33-18-32-RURAL | ST_MultiPolygon |
| 18-15590-007 | SIBLEY RD | 28-21-33-RURAL | ST_MultiPolygon |
| 21-00272-420 | 5392 AR 112 HWY | 13-18-31-SPRINGDALE | ST_MultiPolygon |
| 21-01419-000 | | SPRING HILL SUB-SPRINGDALE | ST_MultiPolygon |
| 22-00258-000 | 645 E 1ST AVE | 07-18-31-HIGHFILL | ST_MultiPolygon |
| 24-00032-010 | US 62 HWY | 14-21-28-GATEWAY | ST_MultiPolygon |

## Issue Type

All 66 invalid geometries have **Ring Self-intersection** errors. This is a common issue with complex polygon boundaries where:
- The polygon boundary crosses over itself
- Usually caused by digitization errors in the source GIS data
- Does not prevent spatial queries from working
- Can be fixed with `ST_MakeValid(geometry)` if needed

## Impact Assessment

**Severity:** LOW
- Represents only 0.04% of all properties
- PostGIS can still perform spatial operations
- Does not affect core functionality
- Most invalid geometries (27) are in records with NULL parcel_id

## Remediation Options

### Option 1: Fix in Place (Recommended)
```sql
UPDATE properties
SET geometry = ST_MakeValid(geometry)
WHERE NOT ST_IsValid(geometry);
```

### Option 2: Use in Queries
```sql
-- Apply ST_MakeValid on-the-fly in queries
SELECT parcel_id, ST_MakeValid(geometry) as geometry
FROM properties
WHERE parcel_id = '01-05263-000';
```

### Option 3: Document and Monitor
- Current approach: Document these parcels
- Monitor if count increases over time
- Address in future data refresh

## Query to Identify Invalid Geometries

```sql
SELECT
    parcel_id,
    ph_add,
    subdivname,
    ST_GeometryType(geometry) as geom_type
FROM properties
WHERE geometry IS NOT NULL
  AND NOT ST_IsValid(geometry)
ORDER BY parcel_id;
```

---

**Note:** The 27 records with NULL parcel_id and invalid geometry likely represent common areas, rights-of-way, or other non-taxable parcels that are less critical for the assessment fairness analysis.
