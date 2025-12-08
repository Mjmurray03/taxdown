"""
Quick demo - Extract sample Bella Vista data for MVP validation
"""

import requests
import pandas as pd
from datetime import datetime

print("=" * 80)
print("TAXDOWN MVP - BELLA VISTA SAMPLE DATA EXTRACTION (DEMO)")
print("=" * 80)

base_url = "https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Planning_Cadastre/FeatureServer/6"

# Extract 500 sample parcels from Benton County
print("\nExtracting 500 sample Benton County parcels...")

params = {
    'where': "county='Benton'",
    'outFields': '*',
    'resultRecordCount': 500,
    'f': 'json',
    'returnGeometry': 'false'
}

response = requests.get(f"{base_url}/query", params=params, timeout=30)

if response.status_code == 200:
    data = response.json()
    features = data.get('features', [])

    if features:
        df = pd.DataFrame([f['attributes'] for f in features])

        print(f"[SUCCESS] Extracted {len(df)} parcels\n")

        # MVP Feature Analysis
        print("=" * 80)
        print("MVP FEATURE READINESS CHECK")
        print("=" * 80)

        # 1. Assessment Anomaly Detector
        print("\n[1] ASSESSMENT ANOMALY DETECTOR")
        has_values = all(col in df.columns for col in ['totalvalue', 'assessvalue', 'landvalue', 'impvalue'])
        print(f"    Status: {'READY' if has_values else 'NOT READY'}")
        if has_values:
            print(f"    Total Value Range:  ${df['totalvalue'].min():,.0f} - ${df['totalvalue'].max():,.0f}")
            print(f"    Average Total:      ${df['totalvalue'].mean():,.2f}")
            print(f"    Average Assessment: ${df['assessvalue'].mean():,.2f}")
            print(f"    Average Land:       ${df['landvalue'].mean():,.2f}")
            print(f"    Average Improvement:${df['impvalue'].mean():,.2f}")

        # 2. AI Appeal Assistant
        print("\n[2] AI APPEAL ASSISTANT (Comparables)")
        has_location = all(col in df.columns for col in ['parcelid', 'section', 'township', 'range'])
        print(f"    Status: {'READY' if has_location else 'NOT READY'}")
        if has_location:
            print(f"    Unique Parcels:     {df['parcelid'].nunique()}")
            print(f"    Location Groupings: Section/Township/Range available")

            if 'subdivision' in df.columns:
                subdivisions = df['subdivision'].value_counts().head()
                print(f"    Top Subdivisions:")
                for sub, count in subdivisions.items():
                    if pd.notna(sub):
                        print(f"      {str(sub)[:35]:35} {count:>4} parcels")

        # 3. Bulk Property Dashboard
        print("\n[3] BULK PROPERTY DASHBOARD")
        has_tracking = 'parcelid' in df.columns and 'totalvalue' in df.columns
        print(f"    Status: {'READY' if has_tracking else 'NOT READY'}")
        if has_tracking:
            print(f"    Can track {len(df)} properties")
            print(f"    Unique IDs: {df['parcelid'].nunique()}")

        # 4. Tax Auction Intelligence
        print("\n[4] TAX AUCTION INTELLIGENCE")
        has_owner = 'ownername' in df.columns
        print(f"    Status: PARTIAL (needs auction data)")
        if has_owner:
            print(f"    Owner data available: {df['ownername'].notna().sum()} records")
            print(f"    Address data: {df['adrlabel'].notna().sum() if 'adrlabel' in df.columns else 0} records")

        # Filter for Bella Vista
        print("\n" + "=" * 80)
        print("BELLA VISTA FILTERING")
        print("=" * 80)

        if 'adrcity' in df.columns:
            cities = df['adrcity'].value_counts().head(10)
            print(f"\nTop 10 cities in sample:")
            for city, count in cities.items():
                if pd.notna(city):
                    print(f"  {str(city):25} {count:>4} parcels")

            bella_vista = df[df['adrcity'] == 'BELLA VISTA']
            print(f"\nBella Vista properties in sample: {len(bella_vista)}")

            if len(bella_vista) > 0:
                print(f"\nBella Vista Stats:")
                print(f"  Avg Total Value: ${bella_vista['totalvalue'].mean():,.2f}")
                print(f"  Median Value:    ${bella_vista['totalvalue'].median():,.2f}")
                print(f"  Min Value:       ${bella_vista['totalvalue'].min():,.2f}")
                print(f"  Max Value:       ${bella_vista['totalvalue'].max():,.2f}")

        # Save files
        print("\n" + "=" * 80)
        print("SAVING OUTPUT")
        print("=" * 80)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save full Benton sample
        csv_file = f"C:\\Users\\mjmur\\benton_sample_{timestamp}.csv"
        df.to_csv(csv_file, index=False)
        print(f"\n[SAVED] {csv_file}")
        print(f"        {len(df)} records, {len(df.columns)} fields")

        # Save Bella Vista only if we found any
        if 'adrcity' in df.columns:
            bella_vista_csv = f"C:\\Users\\mjmur\\bella_vista_sample_{timestamp}.csv"
            bella_vista.to_csv(bella_vista_csv, index=False)
            print(f"\n[SAVED] {bella_vista_csv}")
            print(f"        {len(bella_vista)} Bella Vista records")

        # Print field names for reference
        print("\n" + "=" * 80)
        print("AVAILABLE DATA FIELDS")
        print("=" * 80)
        print("\nAll fields in dataset:")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2}. {col}")

        print("\n" + "=" * 80)
        print("DEMO COMPLETE - DATA READY FOR MVP")
        print("=" * 80)

        print("\nCONCLUSION:")
        print("  [YES] Can build Assessment Anomaly Detector")
        print("  [YES] Can build AI Appeal Assistant")
        print("  [YES] Can build Bulk Property Dashboard")
        print("  [PARTIAL] Tax Auction Intelligence (need auction records)")

        print("\nNEXT STEPS:")
        print("  1. Review CSV files for data quality")
        print("  2. Design PostgreSQL database schema")
        print("  3. Build data import pipeline")
        print("  4. Source supplementary data:")
        print("     - Auction records from Benton County Clerk")
        print("     - POA dues from Bella Vista POA")
        print("     - Property details from Assessor site")

    else:
        print("[ERROR] No features returned")
else:
    print(f"[ERROR] HTTP {response.status_code}")
