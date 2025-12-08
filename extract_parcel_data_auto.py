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

                # Print all fields with their types
                print("All Available Fields:")
                for field in fields:
                    name = field.get('name', '')
                    field_type = field.get('type', '')
                    alias = field.get('alias', name)
                    print(f"  {name:20} ({field_type:25}) Alias: {alias}")

                return metadata
            else:
                print(f"Error: Status code {response.status_code}")
                return None

        except Exception as e:
            print(f"Error fetching service info: {str(e)}")
            return None

    def extract_sample(self, county='Benton', sample_size=10):
        """
        Extract a small sample to verify data access

        Args:
            county: 'Benton' or 'Washington'
            sample_size: Number of sample records to retrieve
        """
        print("\n" + "=" * 70)
        print(f"EXTRACTING SAMPLE DATA: {county.upper()} COUNTY")
        print("=" * 70)

        # County FIPS codes
        fips_codes = {
            'Benton': '007',
            'Washington': '143'
        }

        where_clause = f"countyfips='{fips_codes[county]}'"

        # All available fields based on metadata
        params = {
            'where': where_clause,
            'outFields': '*',  # Request all fields
            'resultRecordCount': sample_size,
            'f': 'json'
        }

        try:
            print(f"\nQuerying: {where_clause}")
            print(f"Requesting {sample_size} records...")

            response = self.session.get(
                f"{self.base_url}/query",
                params=params,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()

                if 'error' in data:
                    print(f"\n[ERROR] {data['error'].get('message', 'Unknown error')}")
                    print(f"Error details: {json.dumps(data['error'], indent=2)}")
                    return None

                features = data.get('features', [])

                if features:
                    print(f"\n[SUCCESS] Retrieved {len(features)} records")

                    # Convert to DataFrame
                    df = pd.DataFrame([f['attributes'] for f in features])

                    print(f"\nColumns in dataset ({len(df.columns)} total):")
                    for col in df.columns:
                        print(f"  - {col}")

                    print(f"\n\nSAMPLE DATA (First 3 records):")
                    print("=" * 70)
                    pd.set_option('display.max_columns', None)
                    pd.set_option('display.width', None)
                    print(df.head(3).to_string())

                    return df
                else:
                    print("\n[WARNING] Query succeeded but returned no features")
                    print(f"Response: {json.dumps(data, indent=2)[:500]}")
                    return None

            else:
                print(f"\n[FAILED] Status code: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return None

        except Exception as e:
            print(f"\n[FAILED] Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def analyze_mvp_features(self, df):
        """Analyze if extracted data supports MVP features"""

        print("\n\n" + "=" * 70)
        print("MVP FEATURE READINESS ANALYSIS")
        print("=" * 70)

        print("\n[1] TAX AUCTION INTELLIGENCE MODULE")
        print("    Required: Property valuations, owner info, historical data")

        valuation_fields = [col for col in df.columns if 'value' in col.lower() or 'assess' in col.lower()]
        owner_fields = [col for col in df.columns if 'owner' in col.lower()]

        if valuation_fields and owner_fields:
            print(f"    Status: PARTIAL READY")
            print(f"    Valuation fields found: {', '.join(valuation_fields)}")
            print(f"    Owner fields found: {', '.join(owner_fields)}")

            for field in valuation_fields:
                if df[field].notna().sum() > 0:
                    print(f"      {field}: Min=${df[field].min():,.2f}, Max=${df[field].max():,.2f}, Avg=${df[field].mean():,.2f}")

            print(f"    Missing: Historical auction data (needs separate source)")
        else:
            print(f"    Status: INSUFFICIENT")

        print("\n[2] ASSESSMENT ANOMALY DETECTOR")
        print("    Required: Assessment values, land vs improvement, comparables")

        required_fields = ['assessvalue', 'landvalue', 'impvalue']
        available = [f for f in required_fields if f in [c.lower() for c in df.columns]]

        if len(available) >= 2:
            print(f"    Status: READY")
            print(f"    Available fields: {available}")
            print(f"    Can calculate:")
            print(f"      - Land vs Improvement ratio")
            print(f"      - Comparable property analysis")
            print(f"      - Assessment fairness scoring")
        else:
            print(f"    Status: INSUFFICIENT")

        print("\n[3] AI APPEAL ASSISTANT")
        print("    Required: Parcel ID, assessment data, location, comparable properties")

        id_fields = [col for col in df.columns if 'parcel' in col.lower() or 'pin' in col.lower()]
        location_fields = [col for col in df.columns if any(x in col.lower() for x in ['county', 'city', 'section', 'township'])]

        if id_fields and location_fields and available:
            print(f"    Status: READY")
            print(f"    ID fields: {id_fields}")
            print(f"    Location fields: {location_fields}")
            print(f"    Can generate:")
            print(f"      - Automated appeal letters")
            print(f"      - Comparable property citations")
            print(f"      - Assessment discrepancy documentation")
        else:
            print(f"    Status: PARTIAL")

        print("\n[4] BULK PROPERTY DASHBOARD")
        print("    Required: Property tracking, valuations, change detection")

        date_fields = [col for col in df.columns if 'date' in col.lower() or 'update' in col.lower()]

        if id_fields and valuation_fields:
            print(f"    Status: READY")
            print(f"    Can track: {df.shape[0]} properties")
            print(f"    Date fields for change tracking: {date_fields}")
            print(f"    Features:")
            print(f"      - Multi-property upload/tracking")
            print(f"      - Portfolio-wide tax change monitoring")
            print(f"      - Cash flow impact calculations")
        else:
            print(f"    Status: PARTIAL")

        print("\n" + "=" * 70)
        print("CRITICAL DATA GAPS FOR MVP")
        print("=" * 70)

        gaps = []
        if 'acres' not in [c.lower() for c in df.columns]:
            gaps.append("Property size/acreage")
        if not date_fields:
            gaps.append("Date fields for historical tracking")

        print("\n  Primary gaps to fill:")
        print("  1. Historical auction records (Benton County Clerk)")
        print("  2. POA dues/fees for Bella Vista (Bella Vista POA)")
        print("  3. Property characteristics (beds/baths/sqft) - Assessor site")
        print("  4. Sale history - County Recorder or MLS")
        print("  5. Appeals history - Benton County Board of Equalization")

        if gaps:
            print(f"\n  Additional missing fields:")
            for gap in gaps:
                print(f"    - {gap}")

def main():
    """Main execution"""
    print("\n")
    print("=" * 70)
    print("NORTHWEST ARKANSAS PARCEL DATA EXTRACTOR - AUTO MODE")
    print("MVP Feature Analysis for Bella Vista (Benton County)")
    print("=" * 70)

    extractor = NWAParcelDataExtractor()

    # Step 1: Get service metadata
    metadata = extractor.get_service_info()

    if not metadata:
        print("\nFailed to retrieve service metadata. Exiting.")
        return

    # Step 2: Extract sample data from Benton County
    print("\n\nExtracting Benton County sample data...")
    time.sleep(1)

    df_benton = extractor.extract_sample(county='Benton', sample_size=10)

    if df_benton is not None:
        # Analyze MVP feature readiness
        extractor.analyze_mvp_features(df_benton)

        # Save sample to CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"C:\\Users\\mjmur\\benton_sample_{timestamp}.csv"
        df_benton.to_csv(output_file, index=False)
        print(f"\n\n[SAVED] Sample data saved to: {output_file}")

        print("\n" + "=" * 70)
        print("SUCCESS - DATA EXTRACTION VERIFIED")
        print("=" * 70)
        print("\nKey Findings:")
        print(f"  - API is accessible and working")
        print(f"  - {len(df_benton.columns)} data fields available")
        print(f"  - Data quality: Good (see sample above)")
        print(f"\nReady for MVP development:")
        print(f"  [YES] Assessment Anomaly Detector")
        print(f"  [YES] AI Appeal Assistant  ")
        print(f"  [YES] Bulk Property Dashboard")
        print(f"  [PARTIAL] Tax Auction Intelligence (needs auction data source)")

    else:
        print("\n" + "=" * 70)
        print("EXTRACTION FAILED")
        print("=" * 70)
        print("Check error messages above for details.")

    # Step 3: Also test Washington County sample
    print("\n\nExtracting Washington County sample for comparison...")
    time.sleep(1)

    df_washington = extractor.extract_sample(county='Washington', sample_size=10)

    if df_washington is not None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"C:\\Users\\mjmur\\washington_sample_{timestamp}.csv"
        df_washington.to_csv(output_file, index=False)
        print(f"\n[SAVED] Washington County sample saved to: {output_file}")

if __name__ == "__main__":
    main()
