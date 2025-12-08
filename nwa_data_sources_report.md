# Northwest Arkansas Real Estate Data Sources - Research Report

## Executive Summary

I've identified several active data sources for Northwest Arkansas (Benton & Washington Counties) property data. The best source for programmatic access is the **Arkansas GIS Office FeatureServer API**, which provides comprehensive parcel data for the entire state including both counties.

---

## PRIMARY DATA SOURCES (RANKED BY ACCESSIBILITY)

### 1. Arkansas GIS Office - Parcel FeatureServer API (BEST OPTION)
**Status: ACTIVE & FREE**

**API Endpoint:**
```
https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Planning_Cadastre/FeatureServer/6
```

**Coverage:** All 75 Arkansas counties including Benton & Washington

**Key Features:**
- REST API with JSON, GeoJSON, and PBF format support
- 33 data fields including:
  - Parcel IDs and legal descriptions
  - Owner names and addresses
  - Assessed values (land, improvement, total)
  - Geographic coordinates
  - Township/Range/Section info
  - Update dates

**Query Capabilities:**
- SQL WHERE clauses
- Spatial queries
- Statistics and aggregations
- Pagination support
- OrderBy and Distinct operations

**Example Query (Benton County):**
```
https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Planning_Cadastre/FeatureServer/6/query?where=county='Benton'&outFields=*&f=json
```

**Example Query (Washington County):**
```
https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Planning_Cadastre/FeatureServer/6/query?where=county='Washington'&outFields=*&f=json
```

**Limitations:**
- Data is for "real estate ad valorem tax valuation, research and assessment purposes only"
- Not considered legal boundary data
- Update frequency varies by county

---

### 2. Benton County GIS Hub
**Status: ACTIVE**

**Portal:** https://benton-county-gis-bentonco.hub.arcgis.com/

**Features:**
- Open Data portal with downloadable datasets
- Parcel viewer: https://gis.bentoncountyar.gov/parcels/index.html
- Property search application
- CSV export capability
- WMS/WFS services available

**Access Methods:**
- Interactive web map search
- CSV export from search results
- Potential bulk download from open data portal

**Contact:**
- GIS Department (note: email shown was for Benton County WA, verify for AR)

---

### 3. Fayetteville Open Data Portal
**Status: ACTIVE (BETA)**

**Portal:** https://data-fayetteville-ar.opendata.arcgis.com/

**Coverage:** City of Fayetteville (Washington County)

**Features:**
- ArcGIS Open Data hub
- Searchable data catalog
- Multiple categories including Housing, Business
- Download and API access capabilities
- Currently in beta, content being added regularly

**Official Resources:**
- GIS Maps: https://www.fayetteville-ar.gov/384/GIS-Interactive-Maps
- Data Downloads: https://www.fayetteville-ar.gov/514/Data-Downloads
- Contact: gis@fayetteville-ar.gov

**Notes:**
- Specific parcel datasets need to be located in catalog
- City-specific data (subset of Washington County)
- More detailed than county-level data

---

### 4. Northwest Arkansas Regional Planning Commission (NWARPC)
**Status: ACTIVE**

**Portal:** https://www.nwarpc.org/interactive-gis-maps/

**Coverage:** Benton & Washington Counties

**Features:**
- Interactive GIS maps
- Parcel boundaries
- Subdivisions
- Political boundaries
- Roads, highways, hydrology
- Current aerial imagery

**Access:** Interactive viewing (check for download options)

---

### 5. ARCountyData.com (Benton & Washington Counties)
**Status: ACTIVE BUT RESTRICTED**

**Websites:**
- Benton: https://www.arcountydata.com/county.asp?county=benton
- Washington: https://www.arcountydata.com/county.asp?county=Washington

**Features:**
- Free property search
- Tax collector records
- Owner information
- Property details

**Limitations:**
- Returns 403 Forbidden to automated requests
- Web scraping explicitly prohibited
- Manual search only
- No API or bulk download

---

### 6. actDataScout (Washington County)
**Status: ACTIVE BUT RESTRICTED**

**Website:** https://www.actdatascout.com/RealProperty/Arkansas/Washington

**Features:**
- Real property search
- County-sponsored public records
- 24/7 access

**Limitations:**
- Returns 403 Forbidden to automated requests
- Scraping/automated tools prohibited
- Requires explicit written permission for automated access
- Manual search interface only

---

## RECOMMENDED APPROACH

### For MVP Development:

**PRIMARY DATA SOURCE:**
Use the Arkansas GIS Office FeatureServer API
- Free, no authentication required
- Covers both Benton & Washington counties
- Programmatic access via REST API
- Rich dataset with 33 fields
- Suitable for building automated pipelines

**SUPPLEMENTARY SOURCES:**
1. Fayetteville Open Data Portal (for city-specific data)
2. Benton County GIS Hub (for county-specific enhancements)
3. NWARPC maps (for visual reference/validation)

**AVOID:**
- ARCountyData.com (blocks automation)
- actDataScout.com (blocks automation)

---

## MARKET SELECTION RECOMMENDATION

Based on data accessibility:

**WINNER: TIE - Benton & Washington Counties (Entire NWA Region)**

**Why:**
- Single API covers BOTH counties
- Can target all major cities: Fayetteville, Bentonville, Rogers, Springdale, Bella Vista
- Larger addressable market
- Easier to scale (one data pipeline)

**Market Breakdown:**
1. **Fayetteville** (Washington County)
   - University town
   - Growing tech scene
   - Most robust city-level open data

2. **Bentonville/Rogers** (Benton County)
   - Walmart HQ = affluent market
   - Strong commercial real estate
   - County GIS hub available

3. **Springdale** (Washington County)
   - Industrial/commercial focus
   - Growing Hispanic market

4. **Bella Vista** (Benton County)
   - Retirement community
   - POA adds complexity but niche opportunity

---

## DATA FIELDS AVAILABLE

From Arkansas GIS FeatureServer:

1. **Identification:**
   - objectid
   - parcelid
   - parcellgl

2. **Ownership:**
   - ownername
   - adrlabel (address)

3. **Valuation:**
   - assessvalue
   - impvalue (improvement value)
   - landvalue
   - totalvalue

4. **Location:**
   - county
   - countyfips
   - section
   - township
   - range
   - Shape (geometry)

5. **Metadata:**
   - camadate (CAMA system date)
   - pubdate (publication date)
   - acres
   - lastupdated

---

## NEXT STEPS

1. Test Arkansas GIS API with sample queries
2. Build data extraction pipeline
3. Validate data quality and coverage
4. Identify data gaps (may need to supplement with other sources)
5. Design database schema based on available fields
6. Create automated refresh process
7. Add value-added analytics on top of raw data

---

## CONTACT INFORMATION

**Arkansas GIS Office:**
- Phone: (501) 682-2767
- Email: communication@arkansasgisoffice.org
- Address: 501 Woodlane Street Ste G4, Little Rock, AR 72201

**Fayetteville GIS:**
- Email: gis@fayetteville-ar.gov

**Benton County Assessor:**
- Phone: 479-271-1037
- Website: https://bentoncountyar.gov/assessor/

**Washington County Assessor:**
- Phone: (479) 444-1500
- Website: https://www.washingtoncountyar.gov/government/departments-a-e/assessor

---

## LEGAL DISCLAIMER

Data from Arkansas GIS Office carries this restriction:
"This dataset is for real estate ad valorem tax valuation, research and assessment purposes only, and is not considered a legal boundary. Arkansas law prohibits the use of this data for actual boundary determinations - consult a registered land surveyor for that purpose."

Ensure your use case complies with these terms.
