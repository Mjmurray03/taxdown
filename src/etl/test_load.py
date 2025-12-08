"""Test loader with first 1000 records"""
import sys
sys.path.insert(0, 'C:/taxdown')

from src.etl.load_properties import *

# Override to load only 1000 records
def load_and_transform_data_sample(parquet_path: str):
    """Load first 1000 records for testing"""
    print(f"Loading sample data from {parquet_path}...")
    gdf = gpd.read_parquet(parquet_path)
    gdf = gdf.head(1000)  # Only first 1000
    print(f"Loaded {len(gdf):,} records for testing")

    # Same transformation logic
    if gdf.crs is None:
        gdf = gdf.set_crs('EPSG:3433')
    gdf = gdf.to_crs('EPSG:4326')

    # Check duplicates
    duplicate_mask = gdf['PARCELID'].duplicated(keep=False) & ~gdf['PARCELID'].isna()
    null_mask = gdf['PARCELID'].isna()
    needs_synthetic = null_mask | duplicate_mask

    print(f"Null: {null_mask.sum()}, Duplicates: {duplicate_mask.sum()}, Total synthetic: {needs_synthetic.sum()}")

    # Generate synthetic IDs
    gdf.loc[needs_synthetic, 'synthetic_parcel_id'] = gdf.loc[needs_synthetic].apply(
        generate_synthetic_parcel_id, axis=1
    )
    gdf.loc[needs_synthetic, 'is_synthetic_id'] = True
    gdf.loc[needs_synthetic, 'PARCELID'] = None
    gdf.loc[~needs_synthetic, 'is_synthetic_id'] = False
    gdf.loc[~needs_synthetic, 'synthetic_parcel_id'] = None

    # Monetary conversion
    for col in ['ASSESS_VAL', 'IMP_VAL', 'LAND_VAL', 'TOTAL_VAL']:
        cents_col = col.lower().replace('_val', '_val_cents')
        gdf[cents_col] = (gdf[col] * 100).fillna(0).astype('int64')

    # Column mapping
    column_mapping = {
        'PARCELID': 'parcel_id',
        'ACRE_AREA': 'acre_area',
        'GIS_EST_AC': 'gis_est_ac',
        'OW_NAME': 'ow_name',
        'OW_ADD': 'ow_add',
        'PH_ADD': 'ph_add',
        'TYPE_': 'type_',
        'S_T_R': 's_t_r',
        'SCHL_CODE': 'schl_code',
        'SUBDIVNAME': 'subdivname',
        'Shape_Leng': 'shape_leng',
        'Shape_Area': 'shape_area',
    }

    df_mapped = gdf.rename(columns=column_mapping)
    df_mapped['county'] = 'Benton'
    df_mapped['state'] = 'AR'
    df_mapped['data_quality_score'] = 100
    df_mapped['source_file'] = 'parcels_enriched.parquet'
    df_mapped['is_active'] = True
    df_mapped['geometry_wkt'] = df_mapped['geometry'].apply(lambda geom: geom.wkt)

    if 'total_building_sqft' in df_mapped.columns:
        df_mapped['building_sqft'] = df_mapped['total_building_sqft']

    final_columns = [
        'parcel_id', 'synthetic_parcel_id', 'is_synthetic_id',
        'acre_area', 'gis_est_ac',
        'ow_name', 'ow_add', 'ph_add',
        'type_', 's_t_r', 'schl_code', 'subdivname',
        'assess_val_cents', 'imp_val_cents', 'land_val_cents', 'total_val_cents',
        'shape_leng', 'shape_area',
        'county', 'state',
        'building_sqft',
        'data_quality_score', 'source_file', 'is_active',
        'geometry_wkt'
    ]

    return df_mapped[final_columns].copy()

# Run test
if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()

    database_url = os.getenv('DATABASE_URL_PUBLIC').replace('postgres://', 'postgresql://')
    parquet_path = 'C:/taxdown/data/processed/parcels_enriched.parquet'

    print("Testing with first 1000 records...")
    df = load_and_transform_data_sample(parquet_path)

    engine = create_engine(database_url, poolclass=NullPool)

    # Clear table
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE properties CASCADE"))
        conn.commit()

    # Insert
    batch_insert_properties(df, engine, batch_size=100)
    verify_load(engine)

    print("Test complete!")
