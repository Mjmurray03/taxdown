"""
Bella Vista MVP Data Extractor
Extracts parcel data from Arkansas GIS API for Taxdown MVP development
Focuses on Benton County (Bella Vista location)
"""

import requests
import pandas as pd
from datetime import datetime
import time
import json

class BellaVistaMVPDataExtractor:
    def __init__(self):
        self.base_url = "https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Planning_Cadastre/FeatureServer/6"
        self.session = requests.Session()

    def extract_benton_county_parcels(self, max_records=None, bella_vista_only=False):
        """
        Extract Benton County parcel data

        Args:
            max_records: Limit number of records (None for all 173K+ parcels)
            bella_vista_only: Filter for Bella Vista city only
        """

        print("\n" + "=" * 80)
        print("EXTRACTING BENTON COUNTY PARCEL DATA FOR TAXDOWN MVP")
        print("=" * 80)

        # Build WHERE clause
        if bella_vista_only:
            # Bella Vista filter - need to check what city values exist
            where_clause = "county='Benton' AND adrcity='BELLA VISTA'"
            print("\nTarget: Bella Vista properties only")
        else:
            where_clause = "county='Benton'"
            print("\nTarget: All Benton County properties")

        # MVP-critical fields mapping to features
        mvp_fields = {
            # Core Identification
            'objectid': 'Primary key',
            'parcelid': 'Property identifier',
            'parcellgl': 'Legal description',

            # Owner Info (Tax Auction Intelligence)
            'ownername': 'Current owner name',
            'adrlabel': 'Property address',
            'adrcity': 'City',
            'adrzip5': 'Zip code',

            # Valuation Data (Assessment Anomaly Detector)
            'assessvalue': 'Assessed value for tax',
            'impvalue': 'Improvement (building) value',
            'landvalue': 'Land value',
            'totalvalue': 'Total market value',

            # Location (AI Appeal Assistant - Comparables)
            'section': 'Section',
            'township': 'Township',
            'range': 'Range',
            'str': 'Section-Township-Range',
            'subdivision': 'Subdivision name',
            'nbhd': 'Neighborhood code',

            # Property Characteristics (Comparables)
            'parceltype': 'Property type code',
            'taxarea': 'Acreage',
            'Shape__Area': 'Area in sq meters',

            # Tax Info
            'taxcode': 'Tax district code',

            # Dates (Portfolio Tracking)
            'sourcedate': 'Source document date',
            'camadate': 'CAMA system date',
            'pubdate': 'Publication date'
        }

        fields_list = list(mvp_fields.keys())

        all_records = []
        offset = 0
        batch_size = 1000

        print(f"\nFetching data in batches of {batch_size}...")
        print(f"{'Records':>10} | {'Cumulative':>12} | Status")
        print("-" * 50)

        while True:
            params = {
                'where': where_clause,
                'outFields': ','.join(fields_list),
                'resultRecordCount': batch_size,
                'resultOffset': offset,
                'f': 'json',
                'returnGeometry': 'false'  # Don't need geometry for MVP
            }

            try:
                response = self.session.get(
                    f"{self.base_url}/query",
                    params=params,
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()

                    if 'error' in data:
                        print(f"\nAPI Error: {data['error'].get('message', 'Unknown')}")
                        break

                    features = data.get('features', [])

                    if not features:
                        print(f"{'Complete':>10} | {len(all_records):>12,} | No more data")
                        break

                    # Extract attributes
                    batch_records = [f['attributes'] for f in features]
                    all_records.extend(batch_records)

                    print(f"{len(features):>10,} | {len(all_records):>12,} | OK")

                    # Check limits
                    if max_records and len(all_records) >= max_records:
                        all_records = all_records[:max_records]
                        print(f"\nReached max_records limit: {max_records:,}")
                        break

                    if len(features) < batch_size:
                        print(f"\nExtraction complete - retrieved all available records")
                        break

                    offset += batch_size
                    time.sleep(0.3)  # API throttle

                else:
                    print(f"\nHTTP Error: {response.status_code}")
                    break

            except Exception as e:
                print(f"\nException: {str(e)}")
                break

        if all_records:
            df = pd.DataFrame(all_records)

            print("\n" + "=" * 80)
            print(f"EXTRACTION COMPLETE: {len(df):,} RECORDS")
            print("=" * 80)

            return df
        else:
            print("\nNo records extracted")
            return None

    def analyze_for_mvp(self, df):
        """Analyze extracted data for MVP feature readiness"""

        print("\n" + "=" * 80)
        print("MVP FEATURE READINESS ANALYSIS")
        print("=" * 80)

        # Basic stats
        print(f"\nDataset Overview:")
        print(f"  Total Properties: {len(df):,}")
        print(f"  Data Fields: {len(df.columns)}")
        print(f"  Date Range: {df['pubdate'].min()} to {df['pubdate'].max()}")

        # Valuation analysis
        print(f"\n[1] ASSESSMENT ANOMALY DETECTOR - READY")
        print(f"    Core Data Available:")

        for field in ['totalvalue', 'assessvalue', 'landvalue', 'impvalue']:
            if field in df.columns:
                non_null = df[field].notna().sum()
                pct = (non_null / len(df)) * 100
                avg_val = df[field].mean()
                print(f"      {field:15} {non_null:>8,} ({pct:>5.1f}%)  Avg: ${avg_val:>12,.2f}")

        # Calculate land-to-improvement ratio for anomaly detection
        df['land_to_total_ratio'] = df['landvalue'] / df['totalvalue']
        df['imp_to_total_ratio'] = df['impvalue'] / df['totalvalue']

        print(f"\n    Derived Metrics:")
        print(f"      Avg Land Ratio:        {df['land_to_total_ratio'].mean()*100:.1f}%")
        print(f"      Avg Improvement Ratio: {df['imp_to_total_ratio'].mean()*100:.1f}%")

        # Comparable analysis capability
        print(f"\n[2] AI APPEAL ASSISTANT - READY")
        print(f"    Comparable Groupings Available:")

        if 'subdivision' in df.columns:
            subdivisions = df['subdivision'].value_counts()
            print(f"      Subdivisions:   {len(subdivisions):>6,} unique")
            print(f"      Top 5: ")
            for sub, count in subdivisions.head(5).items():
                if pd.notna(sub):
                    print(f"        {str(sub)[:40]:40} {count:>6,} parcels")

        if 'nbhd' in df.columns:
            neighborhoods = df['nbhd'].value_counts()
            print(f"      Neighborhoods:  {len(neighborhoods):>6,} unique codes")

        if 'parceltype' in df.columns:
            property_types = df['parceltype'].value_counts()
            print(f"      Property Types: {len(property_types):>6,} codes")
            for ptype, count in property_types.head().items():
                if pd.notna(ptype):
                    print(f"        {ptype:10} {count:>8,} parcels")

        # Bulk dashboard capability
        print(f"\n[3] BULK PROPERTY DASHBOARD - READY")
        print(f"    Tracking Capabilities:")
        print(f"      Unique Parcel IDs:  {df['parcelid'].nunique():>8,}")
        print(f"      Date tracking:      sourcedate, camadate, pubdate")
        print(f"      Value tracking:     totalvalue, assessvalue")

        # Tax auction prep
        print(f"\n[4] TAX AUCTION INTELLIGENCE - PARTIAL")
        print(f"    Available:")
        print(f"      Current valuations:  {df['totalvalue'].notna().sum():>8,} properties")
        print(f"      Owner names:         {df['ownername'].notna().sum():>8,} properties")
        print(f"      Property addresses:  {df['adrlabel'].notna().sum():>8,} properties")
        print(f"\n    MISSING (need external sources):")
        print(f"      - Historical auction records")
        print(f"      - Tax delinquency status")
        print(f"      - Auction sale dates")
        print(f"      - Winning bid history")

        # Data gaps
        print(f"\n" + "=" * 80)
        print(f"CRITICAL DATA GAPS TO FILL")
        print(f"=" * 80)

        gaps = [
            ("Bella Vista POA Dues", "Scrape from bellavistapoa.com"),
            ("Property Characteristics", "Beds/baths/sqft from Benton County Assessor"),
            ("Tax Delinquency Status", "Benton County Collector's office"),
            ("Auction History", "County Clerk sale records"),
            ("Appeals History", "Board of Equalization records"),
            ("Sale History (optional)", "MLS or county recorder")
        ]

        print(f"\n{'Gap':30} | Source")
        print("-" * 60)
        for gap, source in gaps:
            print(f"{gap:30} | {source}")

        return df

    def filter_bella_vista(self, df):
        """Filter dataset to Bella Vista properties only"""

        print("\n" + "=" * 80)
        print("FILTERING FOR BELLA VISTA")
        print("=" * 80)

        # Check city values
        if 'adrcity' in df.columns:
            cities = df['adrcity'].value_counts()
            print(f"\nCities in Benton County dataset:")
            for city, count in cities.head(20).items():
                if pd.notna(city):
                    print(f"  {str(city):30} {count:>8,} parcels")

            # Filter for Bella Vista
            bella_vista_df = df[df['adrcity'] == 'BELLA VISTA'].copy()

            print(f"\n[RESULT]")
            print(f"  Total Benton County:    {len(df):>8,} parcels")
            print(f"  Bella Vista only:       {len(bella_vista_df):>8,} parcels")
            print(f"  Percentage:             {(len(bella_vista_df)/len(df)*100):>7.1f}%")

            return bella_vista_df
        else:
            print("Error: 'adrcity' field not found")
            return df

    def save_output(self, df, filename_base='bella_vista_mvp_data'):
        """Save extracted data to CSV"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"C:\\Users\\mjmur\\{filename_base}_{timestamp}.csv"

        df.to_csv(csv_file, index=False)
        print(f"\n[SAVED] {csv_file}")
        print(f"        {len(df):,} records, {len(df.columns)} fields")

        # Also save a summary JSON
        summary = {
            'extraction_date': timestamp,
            'total_records': len(df),
            'fields': list(df.columns),
            'value_stats': {
                'avg_total_value': float(df['totalvalue'].mean()),
                'median_total_value': float(df['totalvalue'].median()),
                'min_total_value': float(df['totalvalue'].min()),
                'max_total_value': float(df['totalvalue'].max())
            }
        }

        json_file = f"C:\\Users\\mjmur\\{filename_base}_{timestamp}_summary.json"
        with open(json_file, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"[SAVED] {json_file}")

        return csv_file

def main():
    """Main execution for Bella Vista MVP data extraction"""

    print("\n")
    print("=" * 80)
    print("TAXDOWN MVP - BELLA VISTA DATA EXTRACTION")
    print("=" * 80)

    extractor = BellaVistaMVPDataExtractor()

    # Step 1: Extract all Benton County data (or use max_records=5000 for testing)
    print("\nStep 1: Extracting Benton County parcel data...")
    print("This will take several minutes for all 173K+ parcels")
    print("\nOptions:")
    print("  1. Extract ALL Benton County parcels (~173,000)")
    print("  2. Extract SAMPLE (5,000 parcels) for testing")

    choice = input("\nEnter choice (1 or 2): ").strip()

    if choice == '1':
        df_benton = extractor.extract_benton_county_parcels(max_records=None)
    else:
        df_benton = extractor.extract_benton_county_parcels(max_records=5000)

    if df_benton is None:
        print("\nExtraction failed. Exiting.")
        return

    # Step 2: Analyze for MVP readiness
    df_benton = extractor.analyze_for_mvp(df_benton)

    # Step 3: Filter for Bella Vista
    df_bella_vista = extractor.filter_bella_vista(df_benton)

    # Step 4: Save both datasets
    print("\n" + "=" * 80)
    print("SAVING OUTPUT FILES")
    print("=" * 80)

    extractor.save_output(df_benton, 'benton_county_full')
    extractor.save_output(df_bella_vista, 'bella_vista_only')

    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE - MVP DATA READY")
    print("=" * 80)

    print("\nNext Steps:")
    print("  1. Load CSV into PostgreSQL database")
    print("  2. Build Assessment Anomaly Detector algorithm")
    print("  3. Create comparable property matching logic")
    print("  4. Source auction data from County Clerk")
    print("  5. Scrape POA dues from Bella Vista POA website")

if __name__ == "__main__":
    main()
