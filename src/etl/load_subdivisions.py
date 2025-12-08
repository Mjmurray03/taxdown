"""
Subdivision Data Loader

This module loads subdivision data from Benton County Subdivisions shapefile
into the PostgreSQL subdivisions table.

Data Source:
- Subdivisions.shp: 4,041 records (EPSG:3433)

Schema Mapping:
- NAME -> name
- CAMA_Name -> cama_name
- Shape_Leng -> shape_leng
- Shape_Area -> shape_area
- geometry -> geometry (transformed to EPSG:4326)

Author: Data Engineering Team
Date: 2025-12-08
"""

import sys
from pathlib import Path
from datetime import datetime
import logging

import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
EPSG_WGS84 = 4326  # Target CRS for database storage
EPSG_AR_STATE_PLANE_NORTH = 3433  # Source CRS
EXPECTED_RECORD_COUNT = 4041  # Expected number of subdivisions


class SubdivisionLoader:
    """Loader for subdivision shapefile data into PostgreSQL."""

    def __init__(self, shapefile_path: str, database_url: str):
        """
        Initialize the subdivision loader.

        Args:
            shapefile_path: Path to Subdivisions.shp
            database_url: PostgreSQL connection string
        """
        self.shapefile_path = Path(shapefile_path)
        self.database_url = database_url
        self.engine = None
        self.stats = {}

    def connect_database(self) -> None:
        """Create database connection."""
        logger.info("Connecting to PostgreSQL database")
        try:
            self.engine = create_engine(self.database_url.replace("postgres://", "postgresql://", 1))
            # Test connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                logger.info(f"Connected to database: {version}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def verify_table_exists(self) -> None:
        """Verify that the subdivisions table exists."""
        logger.info("Verifying subdivisions table exists")
        query = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'subdivisions'
            )
        """)

        with self.engine.connect() as conn:
            result = conn.execute(query)
            exists = result.fetchone()[0]

            if not exists:
                raise RuntimeError(
                    "subdivisions table does not exist. "
                    "Please run migration 001_initial_schema.sql first."
                )

        logger.info("Table verified: subdivisions exists")

    def load_shapefile(self) -> gpd.GeoDataFrame:
        """
        Load subdivisions from shapefile.

        Returns:
            GeoDataFrame with subdivision data
        """
        logger.info(f"Loading subdivisions from {self.shapefile_path}")

        if not self.shapefile_path.exists():
            raise FileNotFoundError(f"Shapefile not found: {self.shapefile_path}")

        gdf = gpd.read_file(self.shapefile_path)

        logger.info(f"Loaded {len(gdf):,} subdivision records")
        logger.info(f"Source CRS: {gdf.crs}")
        logger.info(f"Columns: {list(gdf.columns)}")

        self.stats['records_loaded'] = len(gdf)
        self.stats['source_crs'] = str(gdf.crs)

        return gdf

    def validate_shapefile_data(self, gdf: gpd.GeoDataFrame) -> None:
        """
        Validate shapefile data quality.

        Args:
            gdf: GeoDataFrame to validate
        """
        logger.info("Validating shapefile data")

        # Check record count
        if len(gdf) != EXPECTED_RECORD_COUNT:
            logger.warning(
                f"Record count mismatch: expected {EXPECTED_RECORD_COUNT}, "
                f"got {len(gdf)}"
            )

        # Check for required columns
        required_columns = ['NAME', 'CAMA_Name', 'Shape_Leng', 'Shape_Area', 'geometry']
        missing_columns = set(required_columns) - set(gdf.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Check for null values in key columns
        null_counts = {
            'NAME': gdf['NAME'].isna().sum(),
            'CAMA_Name': gdf['CAMA_Name'].isna().sum(),
            'geometry': gdf['geometry'].isna().sum()
        }

        for col, count in null_counts.items():
            if count > 0:
                logger.warning(f"Found {count} null values in {col}")

        self.stats['null_names'] = int(null_counts['NAME'])
        self.stats['null_cama_names'] = int(null_counts['CAMA_Name'])
        self.stats['null_geometries'] = int(null_counts['geometry'])

        # Check geometry types
        geom_types = gdf.geometry.geom_type.value_counts()
        logger.info(f"Geometry types: {geom_types.to_dict()}")
        self.stats['geometry_types'] = geom_types.to_dict()

        logger.info("Validation complete")

    def transform_data(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Transform shapefile data to match database schema.

        Args:
            gdf: Source GeoDataFrame

        Returns:
            Transformed GeoDataFrame ready for database insertion
        """
        logger.info("Transforming data for database insertion")

        # Transform CRS to WGS84 (EPSG:4326)
        logger.info(f"Transforming CRS from {gdf.crs} to EPSG:{EPSG_WGS84}")
        gdf_transformed = gdf.to_crs(EPSG_WGS84)

        # Ensure all geometries are MultiPolygon (database expects MultiPolygon)
        logger.info("Converting geometries to MultiPolygon")
        from shapely.geometry import MultiPolygon, Polygon

        def to_multipolygon(geom):
            """Convert geometry to MultiPolygon."""
            if geom is None:
                return None
            if isinstance(geom, MultiPolygon):
                return geom
            elif isinstance(geom, Polygon):
                return MultiPolygon([geom])
            else:
                logger.warning(f"Unexpected geometry type: {type(geom)}")
                return geom

        gdf_transformed['geometry'] = gdf_transformed['geometry'].apply(to_multipolygon)

        # Create DataFrame with mapped column names
        df = pd.DataFrame({
            'name': gdf_transformed['NAME'],
            'cama_name': gdf_transformed['CAMA_Name'],
            'shape_leng': gdf_transformed['Shape_Leng'],
            'shape_area': gdf_transformed['Shape_Area'],
            'geometry': gdf_transformed['geometry']
        })

        # Create GeoDataFrame with proper CRS
        result = gpd.GeoDataFrame(df, geometry='geometry', crs=EPSG_WGS84)

        logger.info(f"Transformed {len(result):,} records to EPSG:{EPSG_WGS84}")
        self.stats['records_transformed'] = len(result)

        return result

    def truncate_table(self) -> None:
        """Truncate the subdivisions table before loading."""
        logger.info("Truncating subdivisions table")

        with self.engine.connect() as conn:
            # Use TRUNCATE for performance and to reset sequences
            conn.execute(text("TRUNCATE TABLE subdivisions CASCADE"))
            conn.commit()

        logger.info("Table truncated successfully")

    def load_to_database(self, gdf: gpd.GeoDataFrame) -> None:
        """
        Load GeoDataFrame to PostgreSQL subdivisions table.

        Args:
            gdf: GeoDataFrame to load
        """
        logger.info(f"Loading {len(gdf):,} subdivisions to database")

        try:
            # Use geopandas to_postgis for geometry handling
            # This automatically handles WKB conversion for PostGIS
            gdf.to_postgis(
                name='subdivisions',
                con=self.engine,
                if_exists='append',  # We already truncated
                index=False,
                chunksize=500  # Insert in batches of 500
            )

            logger.info("Database insert complete")
            self.stats['records_inserted'] = len(gdf)

        except Exception as e:
            logger.error(f"Failed to insert data: {e}")
            raise

    def verify_load(self) -> dict:
        """
        Verify that data was loaded correctly.

        Returns:
            Dictionary with verification results
        """
        logger.info("Verifying data load")

        verification = {}

        with self.engine.connect() as conn:
            # Count total records
            result = conn.execute(text("SELECT COUNT(*) FROM subdivisions"))
            count = result.fetchone()[0]
            verification['total_count'] = count
            logger.info(f"Total records in database: {count:,}")

            # Count records with geometries
            result = conn.execute(text(
                "SELECT COUNT(*) FROM subdivisions WHERE geometry IS NOT NULL"
            ))
            geom_count = result.fetchone()[0]
            verification['with_geometry'] = geom_count
            logger.info(f"Records with geometry: {geom_count:,}")

            # Count records with names
            result = conn.execute(text(
                "SELECT COUNT(*) FROM subdivisions WHERE name IS NOT NULL"
            ))
            name_count = result.fetchone()[0]
            verification['with_name'] = name_count
            logger.info(f"Records with name: {name_count:,}")

            # Sample a few records
            result = conn.execute(text(
                """
                SELECT name, cama_name, shape_leng, shape_area,
                       ST_GeometryType(geometry) as geom_type,
                       ST_SRID(geometry) as srid
                FROM subdivisions
                LIMIT 5
                """
            ))

            logger.info("Sample records:")
            for row in result:
                logger.info(f"  {row.name} | {row.cama_name} | "
                          f"Geom: {row.geom_type} | SRID: {row.srid}")

            # Verify SRID is correct
            result = conn.execute(text(
                "SELECT DISTINCT ST_SRID(geometry) FROM subdivisions WHERE geometry IS NOT NULL"
            ))
            srids = [row[0] for row in result]
            verification['srids'] = srids

            if srids != [EPSG_WGS84]:
                logger.warning(f"Unexpected SRIDs found: {srids}, expected [{EPSG_WGS84}]")
            else:
                logger.info(f"All geometries have correct SRID: {EPSG_WGS84}")

        # Check if count matches expected
        if verification['total_count'] == EXPECTED_RECORD_COUNT:
            logger.info(f"Record count verified: {EXPECTED_RECORD_COUNT:,}")
            verification['count_verified'] = True
        else:
            logger.warning(
                f"Record count mismatch: expected {EXPECTED_RECORD_COUNT:,}, "
                f"got {verification['total_count']:,}"
            )
            verification['count_verified'] = False

        self.stats.update(verification)

        return verification

    def run(self, truncate: bool = True) -> dict:
        """
        Execute the complete subdivision loading pipeline.

        Args:
            truncate: If True, truncate table before loading (default: True)

        Returns:
            Dictionary of pipeline statistics
        """
        start_time = datetime.now()
        logger.info("=" * 80)
        logger.info("SUBDIVISION LOADER STARTED")
        logger.info("=" * 80)

        try:
            # Step 1: Connect to database
            self.connect_database()

            # Step 2: Verify table exists
            self.verify_table_exists()

            # Step 3: Load shapefile
            gdf = self.load_shapefile()

            # Step 4: Validate data
            self.validate_shapefile_data(gdf)

            # Step 5: Transform data
            gdf_transformed = self.transform_data(gdf)

            # Step 6: Truncate table (if requested)
            if truncate:
                self.truncate_table()

            # Step 7: Load to database
            self.load_to_database(gdf_transformed)

            # Step 8: Verify load
            verification = self.verify_load()

            # Calculate execution time
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.stats['execution_time_seconds'] = round(duration, 2)
            self.stats['execution_time_formatted'] = str(end_time - start_time)

            logger.info("=" * 80)
            logger.info(f"LOADER COMPLETED SUCCESSFULLY in {duration:.2f} seconds")
            logger.info("=" * 80)

            return self.stats

        except Exception as e:
            logger.error(f"Loader failed: {e}", exc_info=True)
            raise
        finally:
            if self.engine:
                self.engine.dispose()


def main():
    """Main execution function."""

    # Load environment variables
    load_dotenv()

    # Configuration
    BASE_DIR = Path(__file__).parent.parent.parent
    SHAPEFILE_PATH = BASE_DIR / "data" / "raw" / "Subdivisions" / "Subdivisions.shp"

    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL_PUBLIC')  # Use public URL for Railway
    if not database_url:
        database_url = os.getenv('DATABASE_URL')  # Fallback to internal URL

    if not database_url:
        logger.error("DATABASE_URL not found in environment variables")
        logger.error("Please ensure .env file exists with DATABASE_URL or DATABASE_URL_PUBLIC")
        sys.exit(1)

    logger.info(f"Using database URL: {database_url[:20]}...")  # Log partial URL for security

    # Initialize and run loader
    loader = SubdivisionLoader(
        shapefile_path=str(SHAPEFILE_PATH),
        database_url=database_url
    )

    stats = loader.run(truncate=True)

    # Print summary
    print("\n" + "=" * 80)
    print("SUBDIVISION LOADER STATISTICS")
    print("=" * 80)
    for key, value in sorted(stats.items()):
        print(f"{key}: {value}")
    print("=" * 80)

    # Exit with success if verification passed
    if stats.get('count_verified', False):
        print(f"\nSUCCESS: Loaded {stats['total_count']:,} subdivisions")
        sys.exit(0)
    else:
        print(f"\nWARNING: Loaded {stats.get('total_count', 0):,} subdivisions "
              f"(expected {EXPECTED_RECORD_COUNT:,})")
        sys.exit(1)


if __name__ == "__main__":
    main()
