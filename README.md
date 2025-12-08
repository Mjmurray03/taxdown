# Taxdown MVP - Data Research Files

This folder contains all data research, extraction scripts, and sample data for the Taxdown MVP (Bella Vista property tax intelligence platform).

## Documentation Files

### TAXDOWN_MVP_DATA_SUMMARY.md
**MAIN REFERENCE DOCUMENT** - Complete implementation guide including:
- Primary data source details (Arkansas GIS API)
- All 38 available data fields
- MVP feature readiness analysis
- Critical data gaps to fill
- Implementation plan with timeline
- API usage examples
- Contact information

### nwa_data_sources_report.md
Detailed research report covering:
- All NWA data sources investigated
- Rankings by accessibility
- Recommended approach
- Data field documentation
- Legal disclaimers

## Python Scripts

### Production Scripts

**demo_bella_vista_extraction.py** (RECOMMENDED TO START)
- Quick demonstration script
- Extracts 500 sample Benton County parcels
- Analyzes MVP feature readiness
- Auto-saves CSV files
- Non-interactive, runs automatically
- **USE THIS FIRST** to validate everything works

**extract_bella_vista_mvp_data.py** (FULL PRODUCTION)
- Complete extraction pipeline
- Can extract all 173,180 Benton County parcels
- Bella Vista filtering capability
- Interactive prompts for user control
- Full MVP feature analysis
- Saves both full Benton County and Bella Vista-only datasets

### Testing/Validation Scripts

**test_nwa_data_sources.py**
- Validates all discovered data sources
- Tests API accessibility
- Checks restricted sites (expected to fail)
- Provides recommendations
- Good for understanding what data is available

**test_nwa_locations.py**
- Original location comparison script
- Tests Fayetteville, Bentonville, Rogers, Springdale, Bella Vista
- Determines best market based on data availability
- Historical reference (now superseded by other scripts)

**test_api_direct.py**
- Direct API testing with different query syntaxes
- Helpful for debugging query issues
- Shows raw API responses
- Good for understanding field names and data format

**extract_nwa_parcel_data.py**
- Earlier version with interactive prompts
- Shows service metadata
- Tests query syntax variations
- Good for learning but use newer scripts instead

**extract_parcel_data_auto.py**
- Automated version without user input
- Sample extraction (10 records)
- Good for quick tests
- Simpler than full production version

## Sample Data Files (CSV)

**benton_sample_20251108_173829.csv**
- 200 Benton County parcels
- All 38 data fields
- Includes multiple cities (Rogers, Bentonville, Bella Vista, etc.)
- Good for testing database import

**bella_vista_sample_20251108_173829.csv**
- 5 Bella Vista properties only
- Filtered from the Benton County sample
- Shows Bella Vista-specific data

**arkansas_parcels_sample.csv**
- General Arkansas sample (10 records)
- From various counties
- Shows data format across the state

## Quick Start Guide

### 1. Validate Data Access (First Time)
```bash
python demo_bella_vista_extraction.py
```
This will extract 500 sample parcels and verify all MVP features work.

### 2. Extract Full Dataset
```bash
python extract_bella_vista_mvp_data.py
```
Choose option 1 to extract all 173,180 Benton County parcels.
This will take several minutes.

### 3. Review Documentation
Read `TAXDOWN_MVP_DATA_SUMMARY.md` for:
- Complete implementation plan
- Data gaps that need filling
- Next steps for MVP development

## Key Findings Summary

### Data Source
- **Arkansas GIS Office FeatureServer API** (Free, no auth required)
- URL: https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Planning_Cadastre/FeatureServer/6
- Coverage: 173,180 Benton County parcels (includes Bella Vista)

### MVP Feature Support
- ✅ Assessment Anomaly Detector: READY
- ✅ AI Appeal Assistant: READY
- ✅ Bulk Property Dashboard: READY
- ⚠️ Tax Auction Intelligence: PARTIAL (needs auction history data)

### Critical Data to Source
1. Bella Vista POA Dues (from bellavistapoa.com)
2. Tax Auction History (Benton County Clerk)
3. Tax Delinquency Status (Benton County Collector)
4. Property Details - beds/baths/sqft (Assessor site)

## Available Data Fields (38 total)

### Identification
- objectid, parcelid, parcellgl, countyid

### Owner Info
- ownername, adrlabel, adrcity, adrzip5

### Valuation (CRITICAL)
- totalvalue, assessvalue, landvalue, impvalue

### Location
- section, township, range, subdivision, nbhd

### Property Characteristics
- parceltype, taxarea, Shape__Area

### Dates
- sourcedate, camadate, pubdate

See full documentation for complete field list and descriptions.

## Next Steps

1. **Immediate**: Run demo_bella_vista_extraction.py to validate
2. **Week 1**: Extract full Benton County dataset, set up PostgreSQL
3. **Week 2**: Build Assessment Anomaly Detector algorithm
4. **Week 3**: Source POA dues data
5. **Week 4-6**: Source auction history, build Tax Auction module
6. **Week 7-8**: Complete AI Appeal Assistant and Bulk Dashboard

## Dependencies

Required Python packages:
```bash
pip install requests pandas beautifulsoup4
```

## Support Contacts

**Arkansas GIS Office**
- Phone: (501) 682-2767
- Email: communication@arkansasgisoffice.org

**Benton County Assessor**
- Phone: 479-271-1037

**Bella Vista POA**
- Website: https://bellavistapoa.com/
- Phone: (479) 855-5000

---

Generated: November 8, 2025
For: Taxdown MVP Development
Focus: Bella Vista, Arkansas
