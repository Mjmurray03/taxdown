"""
GIS Data Profiling Script
Loads and profiles all extracted GIS data files
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
import sys
from datetime import datetime

# Data sources to profile
DATA_SOURCES = [
    r"C:\taxdown\data\raw\Parcels (1)\Parcels.shp",
    r"C:\taxdown\data\raw\Subdivisions\Subdivisions.shp",
    r"C:\taxdown\data\raw\Lots\Lots.shp",
    r"C:\taxdown\data\raw\Addresses\Addresses.shp",
    r"C:\taxdown\data\raw\Cities\Cities.shp",
    r"C:\taxdown\data\raw\Arkansas.geojson\Arkansas.geojson"
]

def profile_gis_file(file_path):
    """Profile a single GIS file (shapefile or geojson)"""
    print(f"\nProcessing: {file_path}")

    try:
        # Load the data
        gdf = gpd.read_file(file_path, encoding='utf-8')

        # Basic information
        record_count = len(gdf)
        column_info = gdf.dtypes.to_dict()
        crs = gdf.crs.to_string() if gdf.crs else "No CRS defined"

        # Get sample records (excluding geometry for readability)
        sample_df = gdf.drop(columns=['geometry']).head(3)

        # Identify potential primary key field
        primary_key_candidates = []
        for col in gdf.columns:
            if col.lower() != 'geometry':
                unique_count = gdf[col].nunique()
                if unique_count == record_count and gdf[col].notna().all():
                    primary_key_candidates.append(col)

        # Check for null values in all fields
        null_counts = gdf.isnull().sum()
        null_info = {col: count for col, count in null_counts.items() if count > 0}

        return {
            'file_path': file_path,
            'record_count': record_count,
            'column_info': column_info,
            'crs': crs,
            'sample_records': sample_df,
            'primary_key_candidates': primary_key_candidates,
            'null_info': null_info,
            'success': True,
            'error': None
        }

    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return {
            'file_path': file_path,
            'success': False,
            'error': str(e)
        }

def generate_markdown_report(profiles, output_path):
    """Generate a markdown report from profiling results"""

    report_lines = []
    report_lines.append("# GIS Data Profile Report")
    report_lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_lines.append("---\n")

    for idx, profile in enumerate(profiles, 1):
        if not profile['success']:
            report_lines.append(f"## {idx}. {Path(profile['file_path']).name}")
            report_lines.append(f"\n**Status:** ERROR")
            report_lines.append(f"\n**Error Message:** {profile['error']}\n")
            report_lines.append("---\n")
            continue

        # Header
        file_name = Path(profile['file_path']).name
        report_lines.append(f"## {idx}. {file_name}")
        report_lines.append(f"\n**File Path:** `{profile['file_path']}`\n")

        # Record count
        report_lines.append(f"### Record Count")
        report_lines.append(f"\n**Total Records:** {profile['record_count']:,}\n")

        # CRS Information
        report_lines.append(f"### Coordinate Reference System (CRS)")
        report_lines.append(f"\n```")
        report_lines.append(f"{profile['crs']}")
        report_lines.append(f"```\n")

        # Column Information
        report_lines.append(f"### Column Information")
        report_lines.append("\n| Column Name | Data Type |")
        report_lines.append("|-------------|-----------|")
        for col, dtype in profile['column_info'].items():
            report_lines.append(f"| {col} | {dtype} |")
        report_lines.append("")

        # Primary Key Candidates
        report_lines.append(f"### Primary Key / Unique Identifier")
        if profile['primary_key_candidates']:
            report_lines.append(f"\n**Identified Primary Key Candidate(s):** {', '.join(profile['primary_key_candidates'])}")
            report_lines.append(f"\n*Note: These fields have unique values for all records with no nulls.*\n")
        else:
            report_lines.append(f"\n**No unique identifier field found.**")
            report_lines.append(f"\n*Note: No single field contains unique non-null values for all records.*\n")

        # Null Value Analysis
        report_lines.append(f"### Null Value Analysis")
        if profile['null_info']:
            report_lines.append("\n| Column Name | Null Count | Percentage |")
            report_lines.append("|-------------|------------|------------|")
            for col, null_count in profile['null_info'].items():
                pct = (null_count / profile['record_count']) * 100
                report_lines.append(f"| {col} | {null_count:,} | {pct:.2f}% |")
            report_lines.append("")
        else:
            report_lines.append(f"\n**No null values found in any fields.**\n")

        # Sample Records
        report_lines.append(f"### Sample Records (3 records, geometry excluded)")
        report_lines.append("\n```")
        report_lines.append(profile['sample_records'].to_string())
        report_lines.append("```\n")

        report_lines.append("---\n")

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    print(f"\nReport saved to: {output_path}")

def main():
    """Main execution function"""
    print("=" * 80)
    print("GIS Data Profiling Script")
    print("=" * 80)

    profiles = []

    # Profile each data source
    for data_source in DATA_SOURCES:
        profile = profile_gis_file(data_source)
        profiles.append(profile)

    # Generate markdown report
    output_path = r"C:\taxdown\docs\data_profile_report.md"

    # Create docs directory if it doesn't exist
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    generate_markdown_report(profiles, output_path)

    print("\n" + "=" * 80)
    print("Profiling Complete!")
    print("=" * 80)

    # Summary
    successful = sum(1 for p in profiles if p['success'])
    failed = len(profiles) - successful
    print(f"\nSummary: {successful} successful, {failed} failed")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
