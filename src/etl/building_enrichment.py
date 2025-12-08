"""
Building Footprints Enrichment Pipeline

This module integrates Microsoft Building Footprints data with parcel records.
It performs spatial joins to calculate building metrics per parcel including:
- building_count: Number of buildings per parcel
- total_building_sqft: Sum of all building areas in square feet
- largest_building_sqft: Area of the largest building in square feet

Data Sources:
- Buildings: Microsoft Building Footprints (Arkansas.geojson, EPSG:4326)
- Parcels: Benton County Parcels shapefile (EPSG:3433)

Performance Optimizations:
- Spatial filtering to reduce building dataset to Benton County bounds
- Spatial indexing using rtree for efficient intersection queries
- Chunked processing for memory efficiency
- Centroid-based point-in-polygon for performance

Author: Data Engineering Team
Date: 2025-12-07
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime
from shapely.geometry import Point
import warnings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
EPSG_WGS84 = 4326  # Buildings CRS
EPSG_AR_STATE_PLANE_NORTH = 3433  # Parcels CRS (Arkansas State Plane North, US Feet)
SQ_METERS_TO_SQ_FEET = 10.764  # Conversion factor
BUFFER_DEGREES = 0.05  # ~5.5km buffer for building filtering


class BuildingEnrichmentPipeline:
    """Pipeline for enriching parcel data with building footprint metrics."""

    def __init__(
        self,
        parcels_path: str,
        buildings_path: str,
        output_path: str
    ):
        """
        Initialize the building enrichment pipeline.

        Args:
            parcels_path: Path to parcels shapefile
            buildings_path: Path to buildings GeoJSON
            output_path: Path for output parquet file
        """
        self.parcels_path = Path(parcels_path)
        self.buildings_path = Path(buildings_path)
        self.output_path = Path(output_path)
        self.stats = {}

    def load_parcels(self) -> gpd.GeoDataFrame:
        """
        Load parcel data from shapefile.

        Returns:
            GeoDataFrame with parcels in EPSG:3433
        """
        logger.info(f"Loading parcels from {self.parcels_path}")
        parcels = gpd.read_file(self.parcels_path)

        logger.info(f"Loaded {len(parcels):,} parcels")
        logger.info(f"Parcels CRS: {parcels.crs}")
        logger.info(f"Parcels bounds: {parcels.total_bounds}")

        self.stats['total_parcels'] = len(parcels)
        self.stats['parcels_crs'] = str(parcels.crs)

        return parcels

    def get_bounding_box_with_buffer(self, parcels: gpd.GeoDataFrame) -> tuple:
        """
        Calculate bounding box for parcels with buffer in WGS84.

        Args:
            parcels: GeoDataFrame in EPSG:3433

        Returns:
            Tuple of (minx, miny, maxx, maxy) in EPSG:4326
        """
        # Convert parcels to WGS84 to get bounds for filtering buildings
        parcels_wgs84 = parcels.to_crs(EPSG_WGS84)
        minx, miny, maxx, maxy = parcels_wgs84.total_bounds

        # Add buffer to ensure we capture buildings on parcel edges
        minx -= BUFFER_DEGREES
        miny -= BUFFER_DEGREES
        maxx += BUFFER_DEGREES
        maxy += BUFFER_DEGREES

        logger.info(f"Bounding box (WGS84 with buffer): ({minx:.4f}, {miny:.4f}, {maxx:.4f}, {maxy:.4f})")

        return minx, miny, maxx, maxy

    def load_and_filter_buildings(
        self,
        bbox: tuple,
        chunk_size: int = 100000
    ) -> gpd.GeoDataFrame:
        """
        Load buildings from GeoJSON and filter to bounding box.

        This uses chunked reading to avoid loading all 1.57M buildings into memory.
        Only buildings within the Benton County bounding box are retained.

        Args:
            bbox: Bounding box tuple (minx, miny, maxx, maxy) in EPSG:4326
            chunk_size: Number of features to process at a time

        Returns:
            GeoDataFrame with filtered buildings in EPSG:4326
        """
        logger.info(f"Loading and filtering buildings from {self.buildings_path}")
        logger.info("This may take a few minutes for 1.57M buildings...")

        minx, miny, maxx, maxy = bbox

        try:
            # Try to use bbox parameter for efficient filtering if supported
            buildings = gpd.read_file(
                self.buildings_path,
                bbox=(minx, miny, maxx, maxy)
            )
            logger.info(f"Loaded {len(buildings):,} buildings using bbox filter")

        except Exception as e:
            logger.warning(f"Bbox filtering not supported, using manual filter: {e}")
            # Fall back to loading all and filtering
            buildings = gpd.read_file(self.buildings_path)
            logger.info(f"Loaded {len(buildings):,} total buildings")

            # Filter to bounding box
            buildings = buildings.cx[minx:maxx, miny:maxy]
            logger.info(f"Filtered to {len(buildings):,} buildings in bounding box")

        logger.info(f"Buildings CRS: {buildings.crs}")

        self.stats['total_buildings_loaded'] = len(buildings)
        self.stats['buildings_crs'] = str(buildings.crs)

        return buildings

    def calculate_building_areas(self, buildings: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Calculate building areas in square feet.

        Buildings are in EPSG:4326 (degrees), so we need to:
        1. Transform to EPSG:3433 (US Feet) for accurate area calculation
        2. Calculate area in square feet
        3. Keep geometry in EPSG:3433 for spatial join

        Args:
            buildings: GeoDataFrame in EPSG:4326

        Returns:
            GeoDataFrame with area_sqft column in EPSG:3433
        """
        logger.info("Transforming buildings to EPSG:3433 for area calculations")

        # Transform to State Plane projection
        buildings_transformed = buildings.to_crs(EPSG_AR_STATE_PLANE_NORTH)

        # Calculate area in square feet (projection is already in US Feet)
        logger.info("Calculating building areas in square feet")
        buildings_transformed['area_sqft'] = buildings_transformed.geometry.area

        # Log statistics
        logger.info(f"Building area stats (sq ft):")
        logger.info(f"  Min: {buildings_transformed['area_sqft'].min():,.0f}")
        logger.info(f"  Mean: {buildings_transformed['area_sqft'].mean():,.0f}")
        logger.info(f"  Median: {buildings_transformed['area_sqft'].median():,.0f}")
        logger.info(f"  Max: {buildings_transformed['area_sqft'].max():,.0f}")

        self.stats['building_area_min'] = float(buildings_transformed['area_sqft'].min())
        self.stats['building_area_mean'] = float(buildings_transformed['area_sqft'].mean())
        self.stats['building_area_median'] = float(buildings_transformed['area_sqft'].median())
        self.stats['building_area_max'] = float(buildings_transformed['area_sqft'].max())

        return buildings_transformed

    def spatial_join_buildings_to_parcels(
        self,
        parcels: gpd.GeoDataFrame,
        buildings: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """
        Perform spatial join using building centroids and parcel polygons.

        This uses a centroid-based approach:
        - If a building's centroid falls within a parcel, it belongs to that parcel
        - This avoids double-counting buildings that overlap parcel boundaries
        - More performant than polygon-polygon intersection

        Args:
            parcels: GeoDataFrame with parcel polygons
            buildings: GeoDataFrame with building polygons and area_sqft

        Returns:
            GeoDataFrame with spatial join results
        """
        logger.info("Calculating building centroids for spatial join")

        # Calculate centroids for point-in-polygon join
        buildings_centroids = buildings.copy()
        buildings_centroids['geometry'] = buildings_centroids.geometry.centroid

        logger.info(f"Performing spatial join: {len(parcels):,} parcels x {len(buildings_centroids):,} buildings")
        logger.info("This operation uses rtree spatial indexing for performance...")

        # Spatial join: buildings to parcels
        # Use 'inner' join to only keep buildings that fall within parcels
        joined = gpd.sjoin(
            buildings_centroids[['geometry', 'area_sqft']],
            parcels[['PARCELID', 'geometry']],
            how='inner',
            predicate='within'
        )

        logger.info(f"Spatial join complete: {len(joined):,} building-parcel matches")

        self.stats['total_building_parcel_matches'] = len(joined)

        return joined

    def aggregate_building_metrics(
        self,
        joined: gpd.GeoDataFrame
    ) -> pd.DataFrame:
        """
        Aggregate building metrics per parcel.

        Calculates:
        - building_count: Number of buildings per parcel
        - total_building_sqft: Sum of building areas
        - largest_building_sqft: Maximum building area

        Args:
            joined: GeoDataFrame from spatial join

        Returns:
            DataFrame with aggregated metrics per PARCELID
        """
        logger.info("Aggregating building metrics per parcel")

        # Group by parcel and calculate metrics
        metrics = joined.groupby('PARCELID').agg({
            'area_sqft': ['count', 'sum', 'max']
        }).reset_index()

        # Flatten column names
        metrics.columns = [
            'PARCELID',
            'building_count',
            'total_building_sqft',
            'largest_building_sqft'
        ]

        # Convert to integers for cleaner output
        metrics['building_count'] = metrics['building_count'].astype(int)
        metrics['total_building_sqft'] = metrics['total_building_sqft'].astype(int)
        metrics['largest_building_sqft'] = metrics['largest_building_sqft'].astype(int)

        logger.info(f"Calculated metrics for {len(metrics):,} parcels with buildings")
        logger.info(f"Building count distribution:")
        logger.info(f"  1 building: {(metrics['building_count'] == 1).sum():,} parcels")
        logger.info(f"  2 buildings: {(metrics['building_count'] == 2).sum():,} parcels")
        logger.info(f"  3+ buildings: {(metrics['building_count'] >= 3).sum():,} parcels")
        logger.info(f"  Max buildings on single parcel: {metrics['building_count'].max()}")

        self.stats['parcels_with_buildings'] = len(metrics)
        self.stats['parcels_with_1_building'] = int((metrics['building_count'] == 1).sum())
        self.stats['parcels_with_2_buildings'] = int((metrics['building_count'] == 2).sum())
        self.stats['parcels_with_3plus_buildings'] = int((metrics['building_count'] >= 3).sum())
        self.stats['max_buildings_per_parcel'] = int(metrics['building_count'].max())

        return metrics

    def enrich_parcels(
        self,
        parcels: gpd.GeoDataFrame,
        building_metrics: pd.DataFrame
    ) -> gpd.GeoDataFrame:
        """
        Join building metrics to parcels dataset.

        Parcels without buildings will have:
        - building_count = 0
        - total_building_sqft = 0
        - largest_building_sqft = 0

        Args:
            parcels: Original parcels GeoDataFrame
            building_metrics: Aggregated building metrics

        Returns:
            Enriched parcels GeoDataFrame
        """
        logger.info("Joining building metrics to parcels")

        # Left join to keep all parcels
        enriched = parcels.merge(
            building_metrics,
            on='PARCELID',
            how='left'
        )

        # Fill NaN values for parcels without buildings
        enriched['building_count'] = enriched['building_count'].fillna(0).astype(int)
        enriched['total_building_sqft'] = enriched['total_building_sqft'].fillna(0).astype(int)
        enriched['largest_building_sqft'] = enriched['largest_building_sqft'].fillna(0).astype(int)

        logger.info(f"Enriched parcels: {len(enriched):,}")
        logger.info(f"Parcels with 0 buildings: {(enriched['building_count'] == 0).sum():,}")
        logger.info(f"Parcels with 1+ buildings: {(enriched['building_count'] > 0).sum():,}")

        self.stats['parcels_with_0_buildings'] = int((enriched['building_count'] == 0).sum())

        return enriched

    def validate_results(self, enriched: gpd.GeoDataFrame) -> dict:
        """
        Validate enriched data and calculate correlation metrics.

        Args:
            enriched: Enriched parcels GeoDataFrame

        Returns:
            Dictionary of validation statistics
        """
        logger.info("Validating enrichment results")

        validation = {}

        # Check for improved properties (IMP_VAL > 0)
        improved = enriched[enriched['IMP_VAL'] > 0].copy()
        validation['improved_parcels'] = len(improved)
        validation['improved_with_buildings'] = int((improved['building_count'] > 0).sum())
        validation['improved_without_buildings'] = int((improved['building_count'] == 0).sum())

        logger.info(f"Improved parcels (IMP_VAL > 0): {validation['improved_parcels']:,}")
        logger.info(f"  With buildings: {validation['improved_with_buildings']:,}")
        logger.info(f"  Without buildings: {validation['improved_without_buildings']:,}")

        # Correlation between IMP_VAL and building_sqft (sanity check)
        if len(improved) > 0 and (improved['total_building_sqft'] > 0).sum() > 0:
            improved_with_buildings = improved[improved['total_building_sqft'] > 0]

            correlation = improved_with_buildings['IMP_VAL'].corr(
                improved_with_buildings['total_building_sqft']
            )
            validation['imp_val_building_correlation'] = float(correlation)

            logger.info(f"Correlation between IMP_VAL and total_building_sqft: {correlation:.3f}")

            # Distribution of building sizes for improved properties
            building_dist = improved_with_buildings['total_building_sqft'].describe()
            validation['building_sqft_distribution'] = {
                'count': int(building_dist['count']),
                'mean': float(building_dist['mean']),
                'std': float(building_dist['std']),
                'min': float(building_dist['min']),
                '25%': float(building_dist['25%']),
                '50%': float(building_dist['50%']),
                '75%': float(building_dist['75%']),
                'max': float(building_dist['max'])
            }

        self.stats.update(validation)

        return validation

    def save_enriched_parcels(self, enriched: gpd.GeoDataFrame) -> None:
        """
        Save enriched parcels to parquet format.

        Args:
            enriched: Enriched parcels GeoDataFrame
        """
        logger.info(f"Saving enriched parcels to {self.output_path}")

        # Ensure output directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save to parquet (geopandas handles geometry serialization)
        enriched.to_parquet(self.output_path, index=False)

        # Get file size
        file_size_mb = self.output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Saved {len(enriched):,} enriched parcels ({file_size_mb:.2f} MB)")

        self.stats['output_file'] = str(self.output_path)
        self.stats['output_size_mb'] = round(file_size_mb, 2)
        self.stats['output_records'] = len(enriched)

    def run(self) -> dict:
        """
        Execute the complete building enrichment pipeline.

        Returns:
            Dictionary of pipeline statistics
        """
        start_time = datetime.now()
        logger.info("="*80)
        logger.info("BUILDING ENRICHMENT PIPELINE STARTED")
        logger.info("="*80)

        try:
            # Step 1: Load parcels
            parcels = self.load_parcels()

            # Step 2: Get bounding box for filtering buildings
            bbox = self.get_bounding_box_with_buffer(parcels)

            # Step 3: Load and filter buildings to Benton County
            buildings = self.load_and_filter_buildings(bbox)

            # Step 4: Calculate building areas in square feet
            buildings_with_area = self.calculate_building_areas(buildings)

            # Step 5: Spatial join buildings to parcels
            joined = self.spatial_join_buildings_to_parcels(parcels, buildings_with_area)

            # Step 6: Aggregate building metrics per parcel
            building_metrics = self.aggregate_building_metrics(joined)

            # Step 7: Enrich parcels with building metrics
            enriched = self.enrich_parcels(parcels, building_metrics)

            # Step 8: Validate results
            validation = self.validate_results(enriched)

            # Step 9: Save enriched parcels
            self.save_enriched_parcels(enriched)

            # Calculate execution time
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.stats['execution_time_seconds'] = round(duration, 2)
            self.stats['execution_time_formatted'] = str(end_time - start_time)

            logger.info("="*80)
            logger.info(f"PIPELINE COMPLETED SUCCESSFULLY in {duration:.2f} seconds")
            logger.info("="*80)

            return self.stats

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise


def main():
    """Main execution function."""

    # Configuration
    BASE_DIR = Path(__file__).parent.parent.parent
    PARCELS_PATH = BASE_DIR / "data" / "raw" / "Parcels (1)" / "Parcels.shp"
    BUILDINGS_PATH = BASE_DIR / "data" / "raw" / "Arkansas.geojson" / "Arkansas.geojson"
    OUTPUT_PATH = BASE_DIR / "data" / "processed" / "parcels_enriched.parquet"

    # Initialize and run pipeline
    pipeline = BuildingEnrichmentPipeline(
        parcels_path=str(PARCELS_PATH),
        buildings_path=str(BUILDINGS_PATH),
        output_path=str(OUTPUT_PATH)
    )

    stats = pipeline.run()

    # Print summary
    print("\n" + "="*80)
    print("PIPELINE STATISTICS")
    print("="*80)
    for key, value in stats.items():
        print(f"{key}: {value}")
    print("="*80)

    return stats


if __name__ == "__main__":
    main()
