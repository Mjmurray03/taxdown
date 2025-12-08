import requests
import json
import time

def test_arkansas_gis_api():
    """
    Test the Arkansas GIS FeatureServer API for parcel data
    """
    print("=" * 70)
    print("TESTING ARKANSAS GIS OFFICE FEATURESERVER API")
    print("=" * 70)

    base_url = "https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Planning_Cadastre/FeatureServer/6"

    # Test 1: Get service metadata
    print("\n[TEST 1] Checking service availability...")
    try:
        response = requests.get(f"{base_url}?f=json", timeout=10)
        if response.status_code == 200:
            metadata = response.json()
            print("  [SUCCESS] Service is online")
            print(f"  [INFO] Service name: {metadata.get('name', 'N/A')}")
            print(f"  [INFO] Total fields available: {len(metadata.get('fields', []))}")
            print(f"  [INFO] Geometry type: {metadata.get('geometryType', 'N/A')}")
        else:
            print(f"  [FAILED] Service returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"  [FAILED] Error: {str(e)}")
        return False

    time.sleep(1)

    # Test 2: Query Benton County parcels (sample)
    print("\n[TEST 2] Querying Benton County parcels (first 5)...")
    try:
        params = {
            'where': "county='Benton'",
            'outFields': 'parcelid,ownername,adrlabel,totalvalue,acres,county',
            'resultRecordCount': 5,
            'f': 'json'
        }
        response = requests.get(f"{base_url}/query", params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if 'features' in data and len(data['features']) > 0:
                print(f"  [SUCCESS] Retrieved {len(data['features'])} Benton County parcels")
                print("\n  Sample parcel:")
                sample = data['features'][0]['attributes']
                for key, value in sample.items():
                    print(f"    {key}: {value}")
            else:
                print("  [WARNING] No features returned")
        else:
            print(f"  [FAILED] Query returned status code: {response.status_code}")
    except Exception as e:
        print(f"  [FAILED] Error: {str(e)}")

    time.sleep(1)

    # Test 3: Query Washington County parcels (sample)
    print("\n[TEST 3] Querying Washington County parcels (first 5)...")
    try:
        params = {
            'where': "county='Washington'",
            'outFields': 'parcelid,ownername,adrlabel,totalvalue,acres,county',
            'resultRecordCount': 5,
            'f': 'json'
        }
        response = requests.get(f"{base_url}/query", params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if 'features' in data and len(data['features']) > 0:
                print(f"  [SUCCESS] Retrieved {len(data['features'])} Washington County parcels")
                print("\n  Sample parcel:")
                sample = data['features'][0]['attributes']
                for key, value in sample.items():
                    print(f"    {key}: {value}")
            else:
                print("  [WARNING] No features returned")
        else:
            print(f"  [FAILED] Query returned status code: {response.status_code}")
    except Exception as e:
        print(f"  [FAILED] Error: {str(e)}")

    time.sleep(1)

    # Test 4: Get count of parcels in each county
    print("\n[TEST 4] Counting total parcels per county...")
    results = {}

    for county in ['Benton', 'Washington']:
        try:
            params = {
                'where': f"county='{county}'",
                'returnCountOnly': 'true',
                'f': 'json'
            }
            response = requests.get(f"{base_url}/query", params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                count = data.get('count', 0)
                results[county] = count
                print(f"  [SUCCESS] {county} County: {count:,} parcels")
            else:
                print(f"  [FAILED] {county} County: Status {response.status_code}")
                results[county] = 0
        except Exception as e:
            print(f"  [FAILED] {county} County: {str(e)}")
            results[county] = 0

        time.sleep(0.5)

    return results

def test_fayetteville_portal():
    """
    Test Fayetteville Open Data Portal accessibility
    """
    print("\n" + "=" * 70)
    print("TESTING FAYETTEVILLE OPEN DATA PORTAL")
    print("=" * 70)

    url = "https://data-fayetteville-ar.opendata.arcgis.com/"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("  [SUCCESS] Portal is accessible")
            print("  [INFO] Status: Beta (content being added)")
            print("  [INFO] Access: https://data-fayetteville-ar.opendata.arcgis.com/")
            print("  [INFO] Contact: gis@fayetteville-ar.gov")
            return True
        else:
            print(f"  [FAILED] Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"  [FAILED] Error: {str(e)}")
        return False

def test_benton_county_gis():
    """
    Test Benton County GIS Hub accessibility
    """
    print("\n" + "=" * 70)
    print("TESTING BENTON COUNTY GIS HUB")
    print("=" * 70)

    url = "https://benton-county-gis-bentonco.hub.arcgis.com/"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("  [SUCCESS] Hub is accessible")
            print("  [INFO] Features: Open Data, Parcel Viewer, WMS/WFS services")
            print("  [INFO] Parcel Viewer: https://gis.bentoncountyar.gov/parcels/index.html")
            return True
        else:
            print(f"  [FAILED] Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"  [FAILED] Error: {str(e)}")
        return False

def test_restricted_sites():
    """
    Test sites that block automated access
    """
    print("\n" + "=" * 70)
    print("TESTING RESTRICTED SITES (Expected to fail)")
    print("=" * 70)

    sites = {
        'ARCountyData (Benton)': 'https://www.arcountydata.com/county.asp?county=benton',
        'actDataScout (Washington)': 'https://www.actdatascout.com/RealProperty/Arkansas/Washington'
    }

    for name, url in sites.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"  [UNEXPECTED] {name}: Accessible (status 200)")
            elif response.status_code == 403:
                print(f"  [EXPECTED] {name}: Blocked (403 Forbidden)")
            else:
                print(f"  [INFO] {name}: Status {response.status_code}")
        except Exception as e:
            print(f"  [ERROR] {name}: {str(e)[:50]}")

        time.sleep(1)

def generate_recommendations(api_results):
    """
    Generate recommendations based on test results
    """
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)

    total_parcels = sum(api_results.values())

    print(f"\n[PRIMARY DATA SOURCE]")
    print(f"  Arkansas GIS FeatureServer API")
    print(f"  Total NWA Parcels Available: {total_parcels:,}")
    print(f"    - Benton County: {api_results.get('Benton', 0):,} parcels")
    print(f"    - Washington County: {api_results.get('Washington', 0):,} parcels")

    print(f"\n[TARGET MARKET]")
    print(f"  ENTIRE NORTHWEST ARKANSAS REGION")
    print(f"  Rationale:")
    print(f"    - Single API covers both counties")
    print(f"    - Larger addressable market ({total_parcels:,} properties)")
    print(f"    - All major cities: Fayetteville, Bentonville, Rogers, Springdale")
    print(f"    - One data pipeline = easier to maintain")

    print(f"\n[IMPLEMENTATION STRATEGY]")
    print(f"  1. Build ETL pipeline using Arkansas GIS API")
    print(f"  2. Start with one county to validate (suggest: Benton)")
    print(f"  3. Expand to both counties once proven")
    print(f"  4. Supplement with Fayetteville data for city-specific insights")
    print(f"  5. Add Benton County GIS data as needed for enrichment")

    print(f"\n[NEXT STEPS]")
    print(f"  1. Write data extraction script for Arkansas GIS API")
    print(f"  2. Design database schema for parcel data")
    print(f"  3. Build automated refresh pipeline (check update frequency)")
    print(f"  4. Create analytics layer (price per sqft, trends, etc.)")
    print(f"  5. Build MVP product on top of clean data")

    print(f"\n[API ENDPOINT TO USE]")
    print(f"  https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Planning_Cadastre/FeatureServer/6/query")

    print(f"\n[AVOID]")
    print(f"  - ARCountyData.com (blocks automation)")
    print(f"  - actDataScout.com (blocks automation)")

if __name__ == "__main__":
    print("\n")
    print("=" * 70)
    print("NORTHWEST ARKANSAS DATA SOURCE ANALYSIS")
    print("Testing all available data sources for real estate data")
    print("=" * 70)

    # Run all tests
    api_results = test_arkansas_gis_api()
    test_fayetteville_portal()
    test_benton_county_gis()
    test_restricted_sites()

    # Generate recommendations
    if api_results:
        generate_recommendations(api_results)

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("See detailed report in: nwa_data_sources_report.md")
    print("=" * 70)
    print()
