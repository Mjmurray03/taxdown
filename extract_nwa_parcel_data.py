import requests
import json
import pandas as pd
from datetime import datetime
import time

class NWAParcelDataExtractor:
    """
    Extract parcel data from Arkansas GIS API for Northwest Arkansas
    Focused on Bella Vista and Benton County for MVP
    """

    def __init__(self):
        self.base_url = "https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Planning_Cadastre/FeatureServer/6"
        self.session = requests.Session()

    def get_service_info(self):
        """Get metadata about the service including all available fields"""
        print("Fetching service metadata...")

        try:
            response = self.session.get(f"{self.base_url}?f=json", timeout=15)
            if response.status_code == 200:
                metadata = response.json()

                print("\n" + "=" * 70)
                print("ARKANSAS GIS PARCEL SERVICE - AVAILABLE FIELDS")
                print("=" * 70)

                fields = metadata.get('fields', [])
                print(f"\nTotal fields available: {len(fields)}\n")

                # Categorize fields for MVP features
                field_categories = {
                    'Identification': [],
                    'Owner Information': [],
                    'Valuation (Assessment Data)': [],
                    'Location/Geography': [],
                    'Property Characteristics': [],
                    'Dates/Metadata': []
                }

                for field in fields:
                    name = field.get('name', '')
                    field_type = field.get('type', '')
                    alias = field.get('alias', name)

                    # Categorize fields
                    if 'parcel' in name.lower() or 'pin' in name.lower() or name.lower() in ['objectid']:
                        field_categories['Identification'].append(f"{name} ({field_type}): {alias}")
                    elif 'owner' in name.lower() or 'addr' in name.lower():
                        field_categories['Owner Information'].append(f"{name} ({field_type}): {alias}")
                    elif 'value' in name.lower() or 'assess' in name.lower() or 'tax' in name.lower():
                        field_categories['Valuation (Assessment Data)'].append(f"{name} ({field_type}): {alias}")
                    elif 'county' in name.lower() or 'section' in name.lower() or 'township' in name.lower() or 'city' in name.lower():
                        field_categories['Location/Geography'].append(f"{name} ({field_type}): {alias}")
                    elif 'acres' in name.lower() or 'area' in name.lower() or 'landuse' in name.lower() or 'zone' in name.lower():
                        field_categories['Property Characteristics'].append(f"{name} ({field_type}): {alias}")
                    elif 'date' in name.lower() or 'update' in name.lower() or 'year' in name.lower():
                        field_categories['Dates/Metadata'].append(f"{name} ({field_type}): {alias}")

                for category, field_list in field_categories.items():
                    if field_list:
                        print(f"\n[{category}]")
                        for field_info in field_list:
                            print(f"  - {field_info}")

                return metadata
            else:
                print(f"Error: Status code {response.status_code}")
                return None

        except Exception as e:
            print(f"Error fetching service info: {str(e)}")
            return None

    def test_query_syntax(self):
        """Test different query syntaxes to find what works"""
        print("\n" + "=" * 70)
        print("TESTING QUERY SYNTAX")
        print("=" * 70)

        test_queries = [
            {
                'name': 'Test 1: Simple Benton query',
                'params': {
                    'where': "COUNTY='Benton'",
                    'outFields': '*',
                    'resultRecordCount': 2,
                    'f': 'json'
                }
            },
            {
                'name': 'Test 2: Benton with UPPER',
                'params': {
                    'where': "UPPER(COUNTY)='BENTON'",
                    'outFields': '*',
                    'resultRecordCount': 2,
                    'f': 'json'
                }
            },
            {
                'name': 'Test 3: CountyFIPS code (Benton=007)',
                'params': {
                    'where': "COUNTYFIPS='007'",
                    'outFields': '*',
                    'resultRecordCount': 2,
                    'f': 'json'
                }
            },
            {
                'name': 'Test 4: Generic query (1=1)',
                'params': {
                    'where': "1=1",
                    'outFields': '*',
                    'resultRecordCount': 2,
                    'f': 'json'
                }
            }
        ]

        for test in test_queries:
            print(f"\n{test['name']}")
            print(f"  WHERE clause: {test['params']['where']}")

            try:
                response = self.session.get(
                    f"{self.base_url}/query",
                    params=test['params'],
                    timeout=15
                )

                if response.status_code == 200:
                    data = response.json()

                    if 'error' in data:
                        print(f"  [ERROR] {data['error'].get('message', 'Unknown error')}")
                    elif 'features' in data and len(data['features']) > 0:
                        print(f"  [SUCCESS] Retrieved {len(data['features'])} features")

                        # Show sample data
                        sample = data['features'][0]['attributes']
                        print(f"\n  Sample fields (first record):")
                        for key, value in list(sample.items())[:10]:
                            print(f"    {key}: {value}")

                        return test['params']['where']  # Return working WHERE clause
                    else:
                        print(f"  [WARNING] Query succeeded but returned no features")
                else:
                    print(f"  [FAILED] Status code: {response.status_code}")

            except Exception as e:
                print(f"  [FAILED] Error: {str(e)}")

            time.sleep(1)

        return None

    def extract_parcels(self, county, max_records=None, output_file=None):
        """
        Extract parcel data for a specific county

        Args:
            county: 'Benton' or 'Washington' or 'ALL'
            max_records: Maximum number of records to retrieve (None for all)
            output_file: Path to save CSV output
        """
        print("\n" + "=" * 70)
        print(f"EXTRACTING PARCEL DATA: {county.upper()}")
        print("=" * 70)

        # Determine WHERE clause based on county
        if county.upper() == 'BENTON':
            where_clause = "COUNTYFIPS='007'"
        elif county.upper() == 'WASHINGTON':
            where_clause = "COUNTYFIPS='143'"
        elif county.upper() == 'ALL':
            where_clause = "COUNTYFIPS IN ('007','143')"
        else:
            print(f"Invalid county: {county}")
            return None

        # Fields needed for MVP features
        mvp_fields = [
            # Identification
            'OBJECTID', 'PARCELID', 'PARCELLGL',

            # Owner Info (for Tax Auction Intelligence)
            'OWNERNAME', 'ADRLABEL',

            # Valuation (for Assessment Anomaly Detector)
            'ASSESSVALUE', 'IMPVALUE', 'LANDVALUE', 'TOTALVALUE',

            # Location (for Bulk Property Dashboard)
            'COUNTY', 'COUNTYFIPS', 'SECTION', 'TOWNSHIP', 'RANGE',

            # Property Characteristics (for Comparable Analysis)
            'ACRES',

            # Dates (for tracking changes over time)
            'CAMADATE', 'PUBDATE', 'LASTUPDATED'
        ]

        all_features = []
        offset = 0
        batch_size = 1000

        while True:
            params = {
                'where': where_clause,
                'outFields': ','.join(mvp_fields),
                'resultRecordCount': batch_size,
                'resultOffset': offset,
                'f': 'json'
            }

            try:
                print(f"\nFetching records {offset} to {offset + batch_size}...")
                response = self.session.get(
                    f"{self.base_url}/query",
                    params=params,
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()

                    if 'error' in data:
                        print(f"Error: {data['error'].get('message', 'Unknown error')}")
                        break

                    features = data.get('features', [])

                    if not features:
                        print("No more features to retrieve.")
                        break

                    all_features.extend(features)
                    print(f"  Retrieved {len(features)} features (Total: {len(all_features)})")

                    # Check if we've hit max_records
                    if max_records and len(all_features) >= max_records:
                        all_features = all_features[:max_records]
                        print(f"\nReached max_records limit: {max_records}")
                        break

                    # Check if we've retrieved all available features
                    if len(features) < batch_size:
                        print("\nRetrieved all available features.")
                        break

                    offset += batch_size
                    time.sleep(0.5)  # Be respectful to the API

                else:
                    print(f"Error: Status code {response.status_code}")
                    break

            except Exception as e:
                print(f"Error: {str(e)}")
                break

        if all_features:
            # Convert to DataFrame
            df = pd.DataFrame([f['attributes'] for f in all_features])

            print("\n" + "=" * 70)
            print("EXTRACTION COMPLETE")
            print("=" * 70)
            print(f"\nTotal records extracted: {len(df)}")
            print(f"\nColumns available:")
            for col in df.columns:
                print(f"  - {col}")

            print(f"\nData Summary:")
            print(df.info())

            print(f"\nSample Data (first 3 records):")
            print(df.head(3))

            # MVP Feature Analysis
            print("\n" + "=" * 70)
            print("MVP FEATURE READINESS ANALYSIS")
            print("=" * 70)

            self.analyze_mvp_readiness(df)

            # Save to file if specified
            if output_file:
                df.to_csv(output_file, index=False)
                print(f"\n[SAVED] Data exported to: {output_file}")

            return df
        else:
            print("\nNo features extracted.")
            return None

    def analyze_mvp_readiness(self, df):
        """Analyze if extracted data supports MVP features"""

        print("\n[1] Tax Auction Intelligence Module")
        print("  Required: Property valuations, owner info, historical data")
        if 'TOTALVALUE' in df.columns and 'OWNERNAME' in df.columns:
            print("  Status: PARTIAL - Has current valuations and ownership")
            print("  Missing: Historical auction data (need separate source)")
            print(f"  Available values range: ${df['TOTALVALUE'].min():,.2f} - ${df['TOTALVALUE'].max():,.2f}")
        else:
            print("  Status: INSUFFICIENT")

        print("\n[2] Assessment Anomaly Detector")
        print("  Required: Assessment values, land vs improvement values, location")
        if all(col in df.columns for col in ['ASSESSVALUE', 'LANDVALUE', 'IMPVALUE', 'ACRES']):
            print("  Status: READY")
            print(f"  Total parcels for comparable analysis: {len(df):,}")
            print(f"  Avg assessment value: ${df['ASSESSVALUE'].mean():,.2f}")
            print(f"  Avg land value: ${df['LANDVALUE'].mean():,.2f}")
            print(f"  Avg improvement value: ${df['IMPVALUE'].mean():,.2f}")
        else:
            print("  Status: INSUFFICIENT")

        print("\n[3] AI Appeal Assistant")
        print("  Required: Assessment data, comparable properties, location data")
        if all(col in df.columns for col in ['ASSESSVALUE', 'ACRES', 'COUNTY', 'PARCELLGL']):
            print("  Status: READY")
            print("  Can generate comparables based on:")
            print("    - Location (County/Section/Township)")
            print("    - Property size (Acres)")
            print("    - Assessment values")
        else:
            print("  Status: INSUFFICIENT")

        print("\n[4] Bulk Property Dashboard")
        print("  Required: Property IDs, valuations, tracking fields")
        if all(col in df.columns for col in ['PARCELID', 'TOTALVALUE', 'LASTUPDATED']):
            print("  Status: READY")
            print("  Can track properties by:")
            print(f"    - Unique Parcel ID: {df['PARCELID'].nunique():,} unique parcels")
            print(f"    - Last updated dates available: {df['LASTUPDATED'].notna().sum():,} records")
        else:
            print("  Status: PARTIAL")

        print("\n[DATA GAPS FOR MVP]")
        print("  1. Historical auction data - Need to source separately")
        print("  2. POA data for Bella Vista - Need separate scraper")
        print("  3. Property characteristics (beds/baths/sqft) - May need assessor site")
        print("  4. Sale history - Need MLS or county recorder data")
        print("  5. Appeal history - Need Benton County appeals records")

def main():
    """Main execution"""
    print("\n")
    print("=" * 70)
    print("NORTHWEST ARKANSAS PARCEL DATA EXTRACTOR")
    print("Focused on Bella Vista & Benton County for MVP")
    print("=" * 70)

    extractor = NWAParcelDataExtractor()

    # Step 1: Get service info and available fields
    metadata = extractor.get_service_info()

    if not metadata:
        print("\nFailed to retrieve service metadata. Exiting.")
        return

    # Step 2: Test query syntax to find working approach
    print("\n\nPRESS ENTER TO CONTINUE TO QUERY TESTING...")
    input()

    working_where = extractor.test_query_syntax()

    if not working_where:
        print("\nCould not find working query syntax. Exiting.")
        return

    # Step 3: Extract sample data for Benton County (Bella Vista is in Benton)
    print("\n\nPRESS ENTER TO EXTRACT BENTON COUNTY SAMPLE DATA (1000 records)...")
    input()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"C:\\Users\\mjmur\\benton_county_parcels_sample_{timestamp}.csv"

    df = extractor.extract_parcels(
        county='Benton',
        max_records=1000,
        output_file=output_file
    )

    if df is not None:
        print("\n" + "=" * 70)
        print("SUCCESS!")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Review the CSV file for data quality")
        print("2. Build database schema based on these fields")
        print("3. Create full extraction script for all Benton County parcels")
        print("4. Add Bella Vista filtering (city or POA designation)")
        print("5. Source supplementary data for gaps identified above")
    else:
        print("\nExtraction failed. Check error messages above.")

if __name__ == "__main__":
    main()
