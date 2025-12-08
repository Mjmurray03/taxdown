# TAXDOWN MVP - Data Extraction Summary

## Executive Summary

Successfully identified and validated data sources for the Taxdown MVP (Bella Vista property tax intelligence platform). The Arkansas GIS Office FeatureServer API provides comprehensive parcel data that supports 3 out of 4 core MVP features immediately.

---

## Data Source Confirmed

**Primary Source:** Arkansas GIS Office - Parcel FeatureServer API

**API Endpoint:**
```
https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Planning_Cadastre/FeatureServer/6
```

**Coverage:**
- All 75 Arkansas counties including Benton County (Bella Vista location)
- 173,180 parcels in Benton County
- Real-time REST API access
- No authentication required
- Free to use

---

## Available Data Fields (38 Total)

### Core Identification
- `objectid` - Primary key
- `parcelid` - Property identifier
- `parcellgl` - Legal description
- `countyid` - County parcel ID

### Owner Information
- `ownername` - Current owner name
- `adrlabel` - Full property address
- `adrcity` - City
- `adrzip5` - Zip code
- `adrnum`, `predir`, `pstrnam`, `pstrtype`, `psufdir` - Address components

### Valuation Data (CRITICAL FOR MVP)
- `totalvalue` - Total market value
- `assessvalue` - Assessed value for tax purposes
- `landvalue` - Land value
- `impvalue` - Improvement (building) value

### Location/Geography
- `section`, `township`, `range` - Public Land Survey System
- `str` - Combined Section-Township-Range
- `subdivision` - Subdivision name
- `nbhd` - Neighborhood code
- `county`, `countyfips` - County identifiers

### Property Characteristics
- `parceltype` - Property type code
- `taxarea` - Acreage
- `Shape__Area` - Area in square meters
- `Shape__Length` - Perimeter length

### Tax Information
- `taxcode` - Tax district code

### Dates/Metadata
- `sourcedate` - Source document date
- `sourceref` - Source document reference
- `camadate` - CAMA system update date
- `pubdate` - Publication date
- `camakey` - CAMA system key
- `camaprov` - CAMA provider
- `dataprov` - Data provider

---

## MVP Feature Readiness

### [READY] Feature 1: Assessment Anomaly Detector

**Status:** FULLY SUPPORTED

**Available Data:**
- Total value, assessed value, land value, improvement value for all parcels
- Can calculate land-to-total ratio and improvement-to-total ratio
- Location data for comparable property matching
- Neighborhood and subdivision groupings

**Sample Stats (from 200-record extract):**
- Average Total Value: $318,161
- Average Assessment: $63,632
- Average Land Value: $97,435
- Average Improvement: $220,726

**Can Build:**
- Comparable property analysis algorithm
- "Fairness Score" (0-100 scale) by comparing to similar properties
- Assessment discrepancy heat maps
- Confidence scoring on potential savings

---

### [READY] Feature 2: AI Appeal Assistant

**Status:** FULLY SUPPORTED

**Available Data:**
- Property identifiers for citation
- Assessment values for discrepancy calculation
- Location data (Section/Township/Range) for comparable selection
- Subdivision and neighborhood codes for grouping
- Owner and address info for appeal documentation

**Can Build:**
- Automated appeal letter generation
- Comparable property citations with specific parcel IDs
- Assessment discrepancy documentation
- Success probability predictor (with historical appeal data if sourced)

---

### [READY] Feature 3: Bulk Property Dashboard

**Status:** FULLY SUPPORTED

**Available Data:**
- Unique parcel IDs for tracking
- Current valuations for all properties
- Date fields (sourcedate, camadate, pubdate) for change detection
- Complete property details for portfolio analysis

**Can Build:**
- Upload/track multiple properties simultaneously
- Portfolio-wide tax change tracking
- Value change monitoring over time
- Cash flow impact calculator
- Export functionality

---

### [PARTIAL] Feature 4: Tax Auction Intelligence Module

**Status:** PARTIALLY SUPPORTED

**Available from API:**
- Current property valuations
- Owner names (200/200 records in sample)
- Property addresses (197/200 records in sample)
- Property characteristics for ROI calculation

**MISSING (Need External Sources):**
- Historical auction data
- Tax delinquency status
- Upcoming auction schedules
- Winning bid history
- Auction success rates

**Required External Sources:**
- Benton County Clerk - Auction records
- Benton County Collector - Tax delinquency data
- Court records - Foreclosure filings

---

## Sample Data Validation

**Test Extraction Results:**
- Successfully extracted 200 Benton County parcels
- 38 data fields available
- 100% data completeness for core fields
- 5 Bella Vista properties identified in sample

**Bella Vista Identification:**
- City field (`adrcity`) contains "BELLA VISTA" value
- Can filter entire dataset for Bella Vista-only properties
- Sample Bella Vista stats:
  - Average Value: $145,467
  - Median Value: $8,000
  - Range: $8,000 - $407,480

**Data Quality:** EXCELLENT
- All critical valuation fields populated
- Owner names present for all records
- Address data 98.5% complete
- Date fields properly formatted

---

## Critical Data Gaps

### 1. Bella Vista POA Dues
**Needed For:** Complete cost analysis for property owners
**Source:** Bella Vista POA website (https://bellavistapoa.com/)
**Extraction:** Web scraping or manual data entry
**Priority:** HIGH (unique to Bella Vista, core differentiator)

### 2. Property Characteristics (Beds/Baths/Square Footage)
**Needed For:** Better comparable property matching
**Source:** Benton County Assessor detailed records
**Extraction:** Scrape from https://www.arcountydata.com/ or assessor site
**Priority:** MEDIUM (improves accuracy but not essential for MVP)

### 3. Tax Auction History
**Needed For:** Tax Auction Intelligence Module
**Source:** Benton County Clerk / Circuit Court
**Extraction:** Public records request or court records scraping
**Priority:** HIGH (core feature)

### 4. Tax Delinquency Status
**Needed For:** Auction opportunity identification
**Source:** Benton County Collector
**Extraction:** May require direct access or public records
**Priority:** HIGH (core feature)

### 5. Appeals History
**Needed For:** Appeal success probability prediction
**Source:** Benton County Board of Equalization
**Extraction:** Public records request
**Priority:** MEDIUM (enhances feature but not essential)

### 6. Sale History (Optional)
**Needed For:** Market value validation
**Source:** County Recorder or MLS
**Extraction:** MLS integration (costly) or recorder scraping
**Priority:** LOW (nice-to-have)

---

## Recommended Implementation Plan

### Phase 1: Core Data Pipeline (Week 1-2)

1. **Database Setup**
   - Design PostgreSQL schema based on 38 available fields
   - Add indexes on parcelid, countyid, adrcity, totalvalue
   - Create views for Bella Vista-only data

2. **Data Extraction**
   - Build automated ETL pipeline using provided Python scripts
   - Extract all 173,180 Benton County parcels
   - Filter and cache Bella Vista subset
   - Schedule daily/weekly updates

3. **Initial Feature Development**
   - Build Assessment Anomaly Detector
   - Create comparable property matching algorithm
   - Implement Fairness Score calculation

### Phase 2: POA Data Integration (Week 3)

1. **POA Dues Scraping**
   - Build scraper for Bella Vista POA website
   - Extract POA dues by property type/location
   - Integrate into database schema
   - Add to cost calculations

### Phase 3: Auction Data Sourcing (Week 4-6)

1. **Historical Data**
   - Contact Benton County Clerk for auction records
   - Request past 3-5 years of data
   - Build import pipeline

2. **Current Data**
   - Identify delinquent property sources
   - Build scraper or API integration
   - Create auction calendar

### Phase 4: Advanced Features (Week 7-8)

1. **AI Appeal Assistant**
   - Integrate Claude API
   - Build letter generation templates
   - Create comparable citation system

2. **Bulk Dashboard**
   - Multi-property upload interface
   - Portfolio analytics
   - Export functionality

---

## API Usage Examples

### Extract All Benton County Parcels
```python
import requests
import pandas as pd

base_url = "https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Planning_Cadastre/FeatureServer/6"

params = {
    'where': "county='Benton'",
    'outFields': '*',
    'resultRecordCount': 1000,
    'resultOffset': 0,
    'f': 'json',
    'returnGeometry': 'false'
}

response = requests.get(f"{base_url}/query", params=params)
data = response.json()
df = pd.DataFrame([f['attributes'] for f in data['features']])
```

### Extract Bella Vista Only
```python
params = {
    'where': "county='Benton' AND adrcity='BELLA VISTA'",
    'outFields': '*',
    'resultRecordCount': 1000,
    'f': 'json'
}
```

### Get Specific Property by Parcel ID
```python
params = {
    'where': f"parcelid='{parcel_id}'",
    'outFields': '*',
    'f': 'json'
}
```

---

## Files Created

1. **nwa_data_sources_report.md** - Complete research findings
2. **test_nwa_data_sources.py** - Data source validation script
3. **extract_bella_vista_mvp_data.py** - Full extraction pipeline (interactive)
4. **demo_bella_vista_extraction.py** - Quick demo extraction (auto)
5. **benton_sample_[timestamp].csv** - Sample data (200 records)
6. **bella_vista_sample_[timestamp].csv** - Bella Vista sample (5 records)
7. **arkansas_parcels_sample.csv** - General Arkansas sample
8. **TAXDOWN_MVP_DATA_SUMMARY.md** - This file

---

## Next Steps

### Immediate (This Week)
1. Run full Benton County extraction using `extract_bella_vista_mvp_data.py`
2. Set up PostgreSQL database
3. Design database schema
4. Build initial import pipeline

### Short-term (Next 2 Weeks)
1. Develop Assessment Anomaly Detector algorithm
2. Build comparable property matching
3. Create Fairness Score calculator
4. Start POA dues research/scraping

### Medium-term (Weeks 3-6)
1. Source auction historical data
2. Build Tax Auction Intelligence module
3. Integrate Claude API for AI Appeal Assistant
4. Develop Bulk Property Dashboard

### Long-term (Weeks 7-8)
1. Complete MVP feature set
2. User testing with Bella Vista properties
3. Refine algorithms based on feedback
4. Prepare for launch

---

## Contact Information

**Arkansas GIS Office**
- Phone: (501) 682-2767
- Email: communication@arkansasgisoffice.org
- Address: 501 Woodlane Street Ste G4, Little Rock, AR 72201

**Benton County Assessor**
- Phone: 479-271-1037
- Website: https://bentoncountyar.gov/assessor/

**Benton County Clerk**
- Phone: 479-271-1013
- Website: https://bentoncountyar.gov/county-clerk/

**Bella Vista POA**
- Website: https://bellavistapoa.com/
- Phone: (479) 855-5000

---

## Conclusion

**DATA READINESS: 75% COMPLETE**

The Arkansas GIS API provides excellent foundation data for Taxdown MVP:

- ✅ Assessment Anomaly Detector - READY
- ✅ AI Appeal Assistant - READY
- ✅ Bulk Property Dashboard - READY
- ⚠️ Tax Auction Intelligence - NEEDS EXTERNAL DATA

**Primary success:** Can build 3 out of 4 core features immediately with available data.

**Key differentiator:** POA dues integration for Bella Vista is the unique value proposition that requires additional sourcing.

**Recommendation:** Proceed with MVP development using Arkansas GIS data while concurrently sourcing auction and POA data.
