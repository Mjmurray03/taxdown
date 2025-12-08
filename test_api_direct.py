import requests
import json
import pandas as pd

# Test the API directly with minimal query
base_url = "https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Planning_Cadastre/FeatureServer/6"

print("Testing Arkansas GIS API with different query approaches...\n")

# Test 1: Get any 10 records without filter
print("=" * 70)
print("TEST 1: Query without WHERE clause (get any 10 records)")
print("=" * 70)

params1 = {
    'where': '1=1',
    'outFields': '*',
    'resultRecordCount': 10,
    'f': 'json'
}

try:
    response = requests.get(f"{base_url}/query", params=params1, timeout=30)
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()

        if 'error' in data:
            print(f"Error: {json.dumps(data['error'], indent=2)}")
        elif 'features' in data and len(data['features']) > 0:
            print(f"SUCCESS! Retrieved {len(data['features'])} features\n")

            # Convert to DataFrame
            df = pd.DataFrame([f['attributes'] for f in data['features']])

            print(f"Columns ({len(df.columns)}): {list(df.columns)}\n")

            # Show first record in detail
            print("FIRST RECORD DETAILS:")
            print("=" * 70)
            first_record = df.iloc[0]
            for col in df.columns:
                value = first_record[col]
                print(f"{col:20} = {value}")

            print("\n\nFULL DATAFRAME:")
            print("=" * 70)
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            pd.set_option('display.max_colwidth', 40)
            print(df)

            # Check which counties are represented
            if 'county' in df.columns:
                print(f"\n\nCOUNTIES IN SAMPLE:")
                print(df['county'].value_counts())

            if 'countyfips' in df.columns:
                print(f"\n\nCOUNTY FIPS IN SAMPLE:")
                print(df['countyfips'].value_counts())

            # Save to CSV
            output_file = "C:\\Users\\mjmur\\arkansas_parcels_sample.csv"
            df.to_csv(output_file, index=False)
            print(f"\n\nSaved to: {output_file}")

        else:
            print(f"No features returned")
            print(f"Response keys: {data.keys()}")

except Exception as e:
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc()

# Test 2: Get count of all records
print("\n\n" + "=" * 70)
print("TEST 2: Get total count of all records")
print("=" * 70)

params2 = {
    'where': '1=1',
    'returnCountOnly': 'true',
    'f': 'json'
}

try:
    response = requests.get(f"{base_url}/query", params=params2, timeout=30)
    if response.status_code == 200:
        data = response.json()
        count = data.get('count', 0)
        print(f"Total records in dataset: {count:,}")
except Exception as e:
    print(f"Error: {str(e)}")

# Test 3: Query for specific counties by name
print("\n\n" + "=" * 70)
print("TEST 3: Try querying by county name")
print("=" * 70)

for county_name in ['Benton', 'Washington', 'BENTON', 'WASHINGTON']:
    params3 = {
        'where': f"county='{county_name}'",
        'returnCountOnly': 'true',
        'f': 'json'
    }

    try:
        response = requests.get(f"{base_url}/query", params=params3, timeout=30)
        if response.status_code == 200:
            data = response.json()
            count = data.get('count', 0)
            print(f"  county='{county_name}': {count:,} records")
    except Exception as e:
        print(f"  county='{county_name}': Error - {str(e)}")
