"""
Load enriched parcel data into Railway PostgreSQL database.

This script:
- Loads parcels_enriched.parquet (173,743 records)
- Maps columns per docs/column_mapping.md
- Converts monetary values to cents (multiply by 100)
- Handles 598 null PARCELIDs with synthetic ID generation
- Transforms geometry from EPSG:3433 to EPSG:4326
- Batch inserts into properties table
"""

import os
import sys
import time
import hashlib
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from shapely import wkt
from shapely.geometry import shape
import psycopg2
from psycopg2.extras import execute_values

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv(project_root / '.env')


def generate_synthetic_parcel_id(row_data) -> str:
    """
    Generate synthetic parcel ID for records with NULL or duplicate PARCELID.
    Uses format: SYNTH-{hash} based on geometry, area, and timestamp for uniqueness.

    Args:
        row_data: Pandas Series with geometry and other columns

    Returns:
        Synthetic parcel ID string
    """
    try:
        geometry = row_data['geometry']
        # Use full geometry WKT, area, and additional fields for better uniqueness
        components = [
            geometry.wkt,
            str(row_data.get('Shape_Area', '')),
            str(row_data.get('Shape_Leng', '')),
            str(row_data.name),  # Row index for ultimate uniqueness
        ]
        combined = '|'.join(components)
        hash_value = hashlib.md5(combined.encode()).hexdigest()[:12].upper()
        return f'SYNTH-{hash_value}'
    except Exception as e:
        # Fallback to timestamp-based hash if geometry is invalid
        random_hash = hashlib.md5(f"{time.time()}{id(row_data)}".encode()).hexdigest()[:12].upper()
        return f'SYNTH-{random_hash}'


def load_and_transform_data(parquet_path: str):
    """
    Load parquet file and transform data for database insertion.

    Args:
        parquet_path: Path to parcels_enriched.parquet

    Returns:
        GeoDataFrame ready for database insertion
    """
    print(f"Loading data from {parquet_path}...")
    print("Reading parquet file (this may take a moment)...")
    start_time = time.time()

    # Read parquet file
    gdf = gpd.read_parquet(parquet_path)
    print(f"Parquet file read completed")

    load_time = time.time() - start_time
    print(f"Loaded {len(gdf):,} records in {load_time:.2f} seconds")
    print(f"Null PARCELID count: {gdf['PARCELID'].isna().sum()}")
    print(f"Building count > 0: {(gdf['building_count'] > 0).sum()}")

    # Ensure geometry is in the correct CRS (source is EPSG:3433)
    if gdf.crs is None:
        print("Setting source CRS to EPSG:3433...")
        gdf = gdf.set_crs('EPSG:3433')

    # Transform geometry from EPSG:3433 to EPSG:4326
    print("Transforming geometry from EPSG:3433 to EPSG:4326...")
    transform_start = time.time()
    gdf = gdf.to_crs('EPSG:4326')
    transform_time = time.time() - transform_start
    print(f"Geometry transformation completed in {transform_time:.2f} seconds")

    # Check for duplicate PARCELID values
    print("Checking for duplicate PARCELID values...")
    parcel_ids = gdf['PARCELID'].dropna()
    duplicate_mask = gdf['PARCELID'].duplicated(keep=False) & ~gdf['PARCELID'].isna()
    duplicate_count = duplicate_mask.sum()
    if duplicate_count > 0:
        print(f"Found {duplicate_count:,} records with duplicate PARCELID values")
        print(f"Top duplicate IDs: {gdf[duplicate_mask]['PARCELID'].value_counts().head(5).to_dict()}")

    # Generate synthetic parcel IDs for:
    # 1. Null PARCELID records (598 records)
    # 2. Duplicate PARCELID records (to ensure uniqueness)
    print("Generating synthetic parcel IDs...")

    null_mask = gdf['PARCELID'].isna()
    needs_synthetic = null_mask | duplicate_mask

    print(f"  - Null PARCELID: {null_mask.sum():,}")
    print(f"  - Duplicate PARCELID: {duplicate_mask.sum():,}")
    print(f"  - Total needing synthetic ID: {needs_synthetic.sum():,}")

    # Generate synthetic IDs - optimized vectorized approach
    # Use row index as unique identifier to avoid expensive apply(axis=1)
    print("Generating synthetic IDs (vectorized)...")
    synthetic_ids = []
    for idx in gdf[needs_synthetic].index:
        # Simple hash based on index for uniqueness
        hash_val = hashlib.md5(f"{idx}_{gdf.loc[idx, 'Shape_Area']}_{gdf.loc[idx, 'Shape_Leng']}".encode()).hexdigest()[:12].upper()
        synthetic_ids.append(f'SYNTH-{hash_val}')

    gdf.loc[needs_synthetic, 'synthetic_parcel_id'] = synthetic_ids
    gdf.loc[needs_synthetic, 'is_synthetic_id'] = True
    print(f"Generated {len(synthetic_ids):,} synthetic IDs")

    # For duplicate parcel IDs, preserve original in parcel_id but it will use synthetic_parcel_id as primary
    # The COALESCE(parcel_id, synthetic_parcel_id) will use parcel_id if not null
    # So we need to set parcel_id to NULL for records that need synthetic IDs to avoid duplicates
    gdf.loc[needs_synthetic, 'PARCELID'] = None

    # For records with unique non-null PARCELID, set is_synthetic_id to False
    gdf.loc[~needs_synthetic, 'is_synthetic_id'] = False
    gdf.loc[~needs_synthetic, 'synthetic_parcel_id'] = None

    # Convert monetary values from dollars to cents (multiply by 100)
    print("Converting monetary values to cents...")
    monetary_columns = ['ASSESS_VAL', 'IMP_VAL', 'LAND_VAL', 'TOTAL_VAL']
    for col in monetary_columns:
        cents_col = col.lower().replace('_val', '_val_cents')
        gdf[cents_col] = (gdf[col] * 100).fillna(0).astype('int64')

    # Map shapefile columns to database columns
    print("Mapping columns to database schema...")
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
        'building_count': 'building_count',
        'total_building_sqft': 'total_building_sqft',
        'largest_building_sqft': 'largest_building_sqft',
    }

    # Select and rename columns
    db_columns = list(column_mapping.values()) + [
        'assess_val_cents', 'imp_val_cents', 'land_val_cents', 'total_val_cents',
        'synthetic_parcel_id', 'is_synthetic_id', 'geometry'
    ]

    # Create DataFrame with mapped columns
    df_mapped = gdf.rename(columns=column_mapping)

    # Add default values for required fields
    df_mapped['county'] = 'Benton'
    df_mapped['state'] = 'AR'
    df_mapped['data_quality_score'] = 100
    df_mapped['source_file'] = 'parcels_enriched.parquet'
    df_mapped['is_active'] = True

    # Convert geometry to WKT for insertion
    print("Converting geometry to WKT...")
    df_mapped['geometry_wkt'] = df_mapped['geometry'].apply(lambda geom: geom.wkt)

    # Select final columns for insertion
    final_columns = [
        'parcel_id', 'synthetic_parcel_id', 'is_synthetic_id',
        'acre_area', 'gis_est_ac',
        'ow_name', 'ow_add', 'ph_add',
        'type_', 's_t_r', 'schl_code', 'subdivname',
        'assess_val_cents', 'imp_val_cents', 'land_val_cents', 'total_val_cents',
        'shape_leng', 'shape_area',
        'county', 'state',
        'data_quality_score', 'source_file', 'is_active',
        'geometry_wkt'
    ]

    # Add building_sqft field if total_building_sqft exists
    # Note: building_count is NOT in the database schema, so we don't include it
    if 'total_building_sqft' in df_mapped.columns:
        # Map total_building_sqft to building_sqft in database
        df_mapped['building_sqft'] = df_mapped['total_building_sqft']
        final_columns.insert(-1, 'building_sqft')

    df_final = df_mapped[final_columns].copy()

    print(f"Data transformation completed. Ready to insert {len(df_final):,} records")

    return df_final


def batch_insert_properties(df: pd.DataFrame, database_url: str, batch_size: int = 5000):
    """
    Insert properties data in batches using fast psycopg2 execute_values.

    Args:
        df: DataFrame with property data
        database_url: Database connection URL
        batch_size: Number of records per batch
    """
    total_records = len(df)
    total_batches = (total_records + batch_size - 1) // batch_size

    print(f"\nStarting batch insertion...")
    print(f"Total records: {total_records:,}")
    print(f"Batch size: {batch_size:,}")
    print(f"Total batches: {total_batches:,}")
    print("-" * 80)

    start_time = time.time()
    inserted_count = 0

    # Use raw psycopg2 connection for faster bulk insert
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    try:
        for batch_num in range(total_batches):
            batch_start = batch_num * batch_size
            batch_end = min(batch_start + batch_size, total_records)
            batch_df = df.iloc[batch_start:batch_end]

            # Prepare data tuples
            values_list = []
            for _, row in batch_df.iterrows():
                values = (
                    None if pd.isna(row.get('parcel_id')) else row['parcel_id'],
                    None if pd.isna(row.get('synthetic_parcel_id')) else row['synthetic_parcel_id'],
                    bool(row.get('is_synthetic_id', False)),
                    None if pd.isna(row.get('acre_area')) else float(row['acre_area']),
                    None if pd.isna(row.get('gis_est_ac')) else float(row['gis_est_ac']),
                    None if pd.isna(row.get('ow_name')) else str(row['ow_name']),
                    None if pd.isna(row.get('ow_add')) else str(row['ow_add']),
                    None if pd.isna(row.get('ph_add')) else str(row['ph_add']),
                    None if pd.isna(row.get('type_')) else str(row['type_']),
                    None if pd.isna(row.get('s_t_r')) else str(row['s_t_r']),
                    None if pd.isna(row.get('schl_code')) else str(row['schl_code']),
                    None if pd.isna(row.get('subdivname')) else str(row['subdivname']),
                    int(row['assess_val_cents']),
                    int(row['imp_val_cents']),
                    int(row['land_val_cents']),
                    int(row['total_val_cents']),
                    None if pd.isna(row.get('shape_leng')) else float(row['shape_leng']),
                    None if pd.isna(row.get('shape_area')) else float(row['shape_area']),
                    str(row['county']),
                    str(row['state']),
                    None if pd.isna(row.get('building_sqft')) else int(row['building_sqft']),
                    int(row['data_quality_score']),
                    str(row['source_file']),
                    bool(row['is_active']),
                    row['geometry_wkt']
                )
                values_list.append(values)

            # Use execute_values for fast batch insert
            insert_sql = """
                INSERT INTO properties (
                    parcel_id, synthetic_parcel_id, is_synthetic_id,
                    acre_area, gis_est_ac,
                    ow_name, ow_add, ph_add,
                    type_, s_t_r, schl_code, subdivname,
                    assess_val_cents, imp_val_cents, land_val_cents, total_val_cents,
                    shape_leng, shape_area,
                    county, state,
                    building_sqft,
                    data_quality_score, source_file, is_active,
                    geometry
                ) VALUES %s
            """

            # Template for each row
            template = """(
                %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s,
                %s,
                %s, %s, %s,
                ST_GeomFromText(%s, 4326)
            )"""

            execute_values(cursor, insert_sql, values_list, template=template, page_size=1000)

            inserted_count += len(batch_df)

            # Report progress every 10,000 records
            if inserted_count % 10000 == 0 or batch_end == total_records:
                elapsed = time.time() - start_time
                rate = inserted_count / elapsed if elapsed > 0 else 0
                pct = (inserted_count / total_records) * 100
                print(f"Progress: {inserted_count:,}/{total_records:,} ({pct:.1f}%) | "
                      f"Rate: {rate:.0f} records/sec | "
                      f"Elapsed: {elapsed:.1f}s")

        # Commit transaction
        conn.commit()
        print("-" * 80)
        print(f"Successfully inserted {inserted_count:,} records")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR during insertion: {e}")
        print("Transaction rolled back")
        raise

    finally:
        cursor.close()
        conn.close()


def verify_load(engine):
    """
    Verify the data load by running validation queries.

    Args:
        engine: SQLAlchemy engine
    """
    print("\n" + "=" * 80)
    print("VERIFICATION QUERIES")
    print("=" * 80)

    with engine.connect() as conn:
        # Total count
        result = conn.execute(text("SELECT COUNT(*) FROM properties"))
        total_count = result.scalar()
        print(f"Total records in properties table: {total_count:,}")

        # Synthetic ID count
        result = conn.execute(text(
            "SELECT COUNT(*) FROM properties WHERE parcel_id IS NULL"
        ))
        null_parcel_count = result.scalar()
        print(f"Records with NULL parcel_id: {null_parcel_count:,}")

        result = conn.execute(text(
            "SELECT COUNT(*) FROM properties WHERE synthetic_parcel_id LIKE 'SYNTH-%'"
        ))
        synthetic_count = result.scalar()
        print(f"Records with synthetic parcel_id (SYNTH-*): {synthetic_count:,}")

        # Building sqft count
        result = conn.execute(text(
            "SELECT COUNT(*) FROM properties WHERE building_sqft > 0"
        ))
        building_count = result.scalar()
        print(f"Records with building_sqft > 0: {building_count:,}")

        # Sample records
        print("\nSample records with synthetic IDs:")
        result = conn.execute(text("""
            SELECT
                parcel_id,
                synthetic_parcel_id,
                is_synthetic_id,
                ow_name,
                total_val_cents / 100.0 as total_val_dollars
            FROM properties
            WHERE synthetic_parcel_id LIKE 'SYNTH-%'
            LIMIT 5
        """))
        for row in result:
            print(f"  {row.synthetic_parcel_id} | {row.ow_name} | ${row.total_val_dollars:,.2f}")

        # Value statistics
        print("\nValue statistics:")
        result = conn.execute(text("""
            SELECT
                COUNT(*) as count,
                MIN(total_val_cents / 100.0) as min_val,
                AVG(total_val_cents / 100.0) as avg_val,
                MAX(total_val_cents / 100.0) as max_val
            FROM properties
            WHERE total_val_cents > 0
        """))
        row = result.fetchone()
        print(f"  Count: {row.count:,}")
        print(f"  Min value: ${row.min_val:,.2f}")
        print(f"  Avg value: ${row.avg_val:,.2f}")
        print(f"  Max value: ${row.max_val:,.2f}")

    print("=" * 80)


def main():
    """Main execution function."""
    print("=" * 80)
    print("TAXDOWN - LOAD PROPERTIES DATA")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Configuration
    parquet_path = str(project_root / 'data' / 'processed' / 'parcels_enriched.parquet')
    database_url = os.getenv('DATABASE_URL_PUBLIC') or os.getenv('DATABASE_URL')

    if not database_url:
        print("ERROR: DATABASE_URL not found in environment variables")
        sys.exit(1)

    # Fix database URL: SQLAlchemy 1.4+ requires postgresql:// not postgres://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    print(f"Database: {database_url.split('@')[1] if '@' in database_url else 'configured'}")
    print(f"Parquet file: {parquet_path}\n")

    # Verify file exists
    if not Path(parquet_path).exists():
        print(f"ERROR: Parquet file not found at {parquet_path}")
        sys.exit(1)

    # Create database engine
    print("Creating database connection...")
    engine = create_engine(
        database_url,
        poolclass=NullPool,  # Disable connection pooling for batch inserts
        echo=False
    )

    try:
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"Connected to PostgreSQL: {version.split(',')[0]}\n")

            # Truncate table without checking (simpler, avoids potential lock issues)
            print("Truncating properties table to start fresh...")
            conn.execute(text("TRUNCATE TABLE properties CASCADE"))
            conn.commit()
            print("Table truncated successfully\n")

        # Load and transform data
        df = load_and_transform_data(parquet_path)

        # Insert data using fast psycopg2 bulk insert
        batch_insert_properties(df, database_url, batch_size=5000)

        # Verify load
        verify_load(engine)

        print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
