"""
Sample Query Script for Enriched Parcels

Demonstrates how to query and analyze the building-enriched parcel dataset.
Shows common use cases for property analysis and data exploration.

Usage:
    python scripts/query_enriched_parcels.py
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path


def load_enriched_parcels(filepath: str = None) -> gpd.GeoDataFrame:
    """Load the enriched parcels dataset."""
    if filepath is None:
        base_dir = Path(__file__).parent.parent
        filepath = base_dir / "data" / "processed" / "parcels_enriched.parquet"

    print(f"Loading enriched parcels from {filepath}")
    parcels = gpd.read_parquet(filepath)
    print(f"Loaded {len(parcels):,} parcels with {len(parcels.columns)} columns")
    return parcels


def query_multi_building_parcels(parcels: gpd.GeoDataFrame, min_buildings: int = 3) -> pd.DataFrame:
    """
    Find parcels with multiple buildings.

    Useful for identifying:
    - Apartment complexes
    - Mobile home parks
    - Commercial developments
    - Multi-unit residential properties
    """
    multi = parcels[parcels['building_count'] >= min_buildings].copy()
    multi = multi.sort_values('building_count', ascending=False)

    result = multi[[
        'PARCELID',
        'OW_NAME',
        'building_count',
        'total_building_sqft',
        'ASSESS_VAL',
        'IMP_VAL'
    ]]

    print(f"\n{'='*80}")
    print(f"Parcels with {min_buildings}+ buildings: {len(result):,}")
    print(f"{'='*80}")
    print(result.head(20).to_string(index=False))

    return result


def query_large_buildings(parcels: gpd.GeoDataFrame, min_sqft: int = 50000) -> pd.DataFrame:
    """
    Find parcels with large buildings.

    Useful for identifying:
    - Commercial warehouses
    - Industrial facilities
    - Large retail stores
    - Office buildings
    """
    large = parcels[parcels['largest_building_sqft'] >= min_sqft].copy()
    large = large.sort_values('largest_building_sqft', ascending=False)

    result = large[[
        'PARCELID',
        'OW_NAME',
        'building_count',
        'largest_building_sqft',
        'total_building_sqft',
        'ASSESS_VAL'
    ]]

    print(f"\n{'='*80}")
    print(f"Parcels with buildings >= {min_sqft:,} sq ft: {len(result):,}")
    print(f"{'='*80}")
    print(result.head(20).to_string(index=False))

    return result


def query_assessment_anomalies(parcels: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Find parcels where improvement value and building area are inconsistent.

    Identifies:
    - Improved parcels (IMP_VAL > 0) without detected buildings
    - Parcels with buildings but zero improvement value
    - Potential data quality issues
    """
    # Case 1: Improved but no building detected
    improved_no_building = parcels[
        (parcels['IMP_VAL'] > 0) &
        (parcels['building_count'] == 0)
    ].copy()

    # Case 2: Building detected but no improvement value
    building_no_improvement = parcels[
        (parcels['building_count'] > 0) &
        (parcels['IMP_VAL'] == 0)
    ].copy()

    print(f"\n{'='*80}")
    print("Assessment Anomalies")
    print(f"{'='*80}")
    print(f"\nImproved parcels without buildings: {len(improved_no_building):,}")
    print(f"Sample records:")
    print(improved_no_building[[
        'PARCELID', 'OW_NAME', 'IMP_VAL', 'building_count'
    ]].head(10).to_string(index=False))

    print(f"\n\nParcels with buildings but no improvement value: {len(building_no_improvement):,}")
    if len(building_no_improvement) > 0:
        print(f"Sample records:")
        print(building_no_improvement[[
            'PARCELID', 'OW_NAME', 'building_count', 'total_building_sqft', 'IMP_VAL'
        ]].head(10).to_string(index=False))

    return improved_no_building, building_no_improvement


def calculate_price_per_sqft(parcels: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Calculate improvement value per square foot.

    Useful for:
    - Comparable property analysis
    - Identifying over/undervalued properties
    - Market analysis by neighborhood
    """
    # Filter to parcels with both improvement value and buildings
    valid = parcels[
        (parcels['IMP_VAL'] > 0) &
        (parcels['total_building_sqft'] > 0)
    ].copy()

    valid['price_per_sqft'] = valid['IMP_VAL'] / valid['total_building_sqft']

    # Remove outliers (> 3 std dev from mean)
    mean = valid['price_per_sqft'].mean()
    std = valid['price_per_sqft'].std()
    valid_filtered = valid[
        (valid['price_per_sqft'] >= mean - 3*std) &
        (valid['price_per_sqft'] <= mean + 3*std)
    ]

    print(f"\n{'='*80}")
    print("Price per Square Foot Analysis")
    print(f"{'='*80}")
    print(f"\nTotal parcels analyzed: {len(valid_filtered):,}")
    print(f"\nStatistics (excluding outliers):")
    print(f"  Mean:   ${valid_filtered['price_per_sqft'].mean():.2f}")
    print(f"  Median: ${valid_filtered['price_per_sqft'].median():.2f}")
    print(f"  Std:    ${valid_filtered['price_per_sqft'].std():.2f}")
    print(f"  Min:    ${valid_filtered['price_per_sqft'].min():.2f}")
    print(f"  Max:    ${valid_filtered['price_per_sqft'].max():.2f}")

    # Top 10 most expensive per sq ft
    print(f"\n\nTop 10 Most Expensive (per sq ft):")
    expensive = valid_filtered.nlargest(10, 'price_per_sqft')[[
        'PARCELID', 'OW_NAME', 'total_building_sqft', 'IMP_VAL', 'price_per_sqft'
    ]]
    print(expensive.to_string(index=False))

    # Top 10 least expensive per sq ft
    print(f"\n\nTop 10 Least Expensive (per sq ft):")
    cheap = valid_filtered.nsmallest(10, 'price_per_sqft')[[
        'PARCELID', 'OW_NAME', 'total_building_sqft', 'IMP_VAL', 'price_per_sqft'
    ]]
    print(cheap.to_string(index=False))

    return valid_filtered


def query_by_property_type(parcels: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Analyze building metrics by property type.

    Shows how building characteristics vary across property types.
    """
    # Group by property type
    type_stats = parcels[parcels['building_count'] > 0].groupby('TYPE_').agg({
        'PARCELID': 'count',
        'building_count': ['mean', 'median', 'max'],
        'total_building_sqft': ['mean', 'median', 'max']
    }).round(0)

    type_stats.columns = [
        'parcel_count',
        'avg_buildings', 'median_buildings', 'max_buildings',
        'avg_sqft', 'median_sqft', 'max_sqft'
    ]

    type_stats = type_stats.sort_values('parcel_count', ascending=False)

    print(f"\n{'='*80}")
    print("Building Metrics by Property Type")
    print(f"{'='*80}")
    print(type_stats.head(20))

    return type_stats


def main():
    """Execute sample queries on enriched parcel data."""

    print("="*80)
    print("ENRICHED PARCELS QUERY EXAMPLES")
    print("="*80)

    # Load data
    parcels = load_enriched_parcels()

    # Query 1: Multi-building parcels
    query_multi_building_parcels(parcels, min_buildings=5)

    # Query 2: Large buildings
    query_large_buildings(parcels, min_sqft=100000)

    # Query 3: Assessment anomalies
    query_assessment_anomalies(parcels)

    # Query 4: Price per square foot
    calculate_price_per_sqft(parcels)

    # Query 5: Property type analysis
    query_by_property_type(parcels)

    print(f"\n{'='*80}")
    print("QUERY EXAMPLES COMPLETE")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
