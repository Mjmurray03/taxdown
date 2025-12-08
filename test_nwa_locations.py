import requests
import json
from bs4 import BeautifulSoup
import time

def test_nwa_locations():
    """
    Test all NWA locations for data accessibility
    Returns the best location based on data availability
    """

    results = {}

    print("=" * 50)
    print("TESTING NWA LOCATIONS FOR FREE DATA ACCESS")
    print("=" * 50)

    # 1. TEST FAYETTEVILLE (Washington County)
    print("\n1. TESTING FAYETTEVILLE...")
    fayetteville_score = 0

    try:
        # Test Fayetteville Open Data Portal
        api_url = "https://services1.arcgis.com/HpNzNWKsFxLpWADz/arcgis/rest/services/Parcels/FeatureServer/0/query"
        params = {
            'where': '1=1',
            'outFields': '*',
            'resultRecordCount': 2,
            'f': 'json'
        }
        response = requests.get(api_url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if 'features' in data and len(data['features']) > 0:
                print("  [SUCCESS] Fayetteville Open Data API: WORKING")
                print(f"  [SUCCESS] Available fields: {list(data['features'][0]['attributes'].keys())[:5]}...")
                fayetteville_score += 10
            else:
                print("  [FAILED] Fayetteville API: No data returned")
        else:
            print("  [FAILED] Fayetteville API: Connection failed")
    except Exception as e:
        print(f"  [FAILED] Fayetteville API Error: {str(e)[:50]}")

    # Test Washington County data
    try:
        wash_url = "https://www.arcountydata.com/county.asp?county=Washington"
        response = requests.get(wash_url, timeout=5)
        if response.status_code == 200 and "Search" in response.text:
            print("  [SUCCESS] Washington County Assessor: ACCESSIBLE")
            fayetteville_score += 5
        else:
            print("  [FAILED] Washington County Assessor: Not accessible")
    except:
        print("  [FAILED] Washington County Assessor: Connection failed")

    results['Fayetteville'] = fayetteville_score
    time.sleep(1)

    # 2. TEST BENTONVILLE/ROGERS (Benton County)
    print("\n2. TESTING BENTONVILLE/ROGERS (Benton County)...")
    benton_score = 0

    try:
        # Test Benton County data access
        benton_url = "https://www.arcountydata.com/county.asp?county=Benton"
        response = requests.get(benton_url, timeout=5)
        if response.status_code == 200 and "Search" in response.text:
            print("  [SUCCESS] Benton County Assessor: ACCESSIBLE")
            benton_score += 5

            # Try to search for a property
            search_url = "https://www.arcountydata.com/search.asp"
            search_data = {
                'county': 'Benton',
                'searchType': 'address',
                'searchString': 'Main'
            }
            search_response = requests.post(search_url, data=search_data, timeout=5)
            if search_response.status_code == 200:
                print("  [SUCCESS] Property search: WORKING")
                benton_score += 3
        else:
            print("  [FAILED] Benton County: Not accessible")
    except Exception as e:
        print(f"  [FAILED] Benton County Error: {str(e)[:50]}")

    # Test Benton County GIS
    try:
        gis_url = "https://bentoncountyar.gov/county-services/gis/"
        response = requests.get(gis_url, timeout=5)
        if response.status_code == 200:
            print("  [SUCCESS] Benton County GIS: Website accessible")
            benton_score += 2
    except:
        print("  [FAILED] Benton County GIS: Not accessible")

    results['Bentonville/Rogers'] = benton_score
    time.sleep(1)

    # 3. TEST SPRINGDALE (Washington County)
    print("\n3. TESTING SPRINGDALE...")
    springdale_score = 0

    try:
        # Springdale uses Washington County data
        spring_url = "https://www.arcountydata.com/county.asp?county=Washington"
        response = requests.get(spring_url, timeout=5)
        if response.status_code == 200:
            print("  [SUCCESS] Washington County Data: ACCESSIBLE")
            springdale_score += 5
    except:
        print("  [FAILED] Springdale: No specific data portal")

    results['Springdale'] = springdale_score
    time.sleep(1)

    # 4. TEST BELLA VISTA (Benton County + POA)
    print("\n4. TESTING BELLA VISTA...")
    bella_vista_score = benton_score  # Inherits Benton County access

    try:
        # Check if POA website has accessible data
        poa_url = "https://bellavistapoa.com/"
        response = requests.get(poa_url, timeout=5)
        if response.status_code == 200:
            print("  [SUCCESS] Bella Vista POA website: ACCESSIBLE")
            if "assessment" in response.text.lower() or "tax" in response.text.lower():
                print("  [WARNING]  POA tax data: May require manual extraction")
                bella_vista_score += 1
    except:
        print("  [FAILED] POA website: Not accessible")

    results['Bella Vista'] = bella_vista_score

    # 5. DETERMINE WINNER
    print("\n" + "=" * 50)
    print("RESULTS SUMMARY:")
    print("=" * 50)

    for location, score in sorted(results.items(), key=lambda x: x[1], reverse=True):
        print(f"{location}: {score}/15 points")

    winner = max(results, key=results.get)

    print("\n" + "=" * 50)
    print(f"WINNER: {winner}")
    print("=" * 50)

    if winner == "Fayetteville":
        print("\nWhy Fayetteville wins:")
        print("- Direct API access (no scraping needed!)")
        print("- Rich parcel data with coordinates")
        print("- University town = more investors")
        print("- Growing tech scene")
    elif winner == "Bentonville/Rogers":
        print("\nWhy Bentonville/Rogers wins:")
        print("- Good assessor data access")
        print("- Walmart HQ = affluent market")
        print("- Active investment community")

    return winner, results

# Run the test!
if __name__ == "__main__":
    winner, scores = test_nwa_locations()

    print("\nNEXT STEPS:")
    print(f"1. Focus your MVP on {winner}")
    print("2. Start building data pipeline for this location")
    print("3. Update business plan to reflect this market")
