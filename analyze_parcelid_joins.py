"""
PARCELID Join Validation Analysis
Validates PARCELID as common identifier across Benton County data sources
Performs spatial joins for datasets without direct PARCELID linkage
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Define paths
BASE_DIR = Path(r"C:\taxdown")
DATA_DIR = BASE_DIR / "data" / "raw"
DOCS_DIR = BASE_DIR / "docs"
DOCS_DIR.mkdir(exist_ok=True)

# Load shapefiles
print("Loading shapefiles...")
print(f"  Loading Parcels from: {DATA_DIR / 'Parcels (1)' / 'Parcels.shp'}")
parcels_gdf = gpd.read_file(DATA_DIR / "Parcels (1)" / "Parcels.shp")
print(f"  Loaded {len(parcels_gdf):,} parcel records")

print(f"  Loading Lots from: {DATA_DIR / 'Lots' / 'Lots.shp'}")
lots_gdf = gpd.read_file(DATA_DIR / "Lots" / "Lots.shp")
print(f"  Loaded {len(lots_gdf):,} lot records")

print(f"  Loading Addresses from: {DATA_DIR / 'Addresses' / 'Addresses.shp'}")
addresses_gdf = gpd.read_file(DATA_DIR / "Addresses" / "Addresses.shp")
print(f"  Loaded {len(addresses_gdf):,} address records")

# Examine column names
print("\n" + "="*80)
print("COLUMN NAME ANALYSIS")
print("="*80)
print(f"\nParcels columns: {list(parcels_gdf.columns)}")
print(f"\nLots columns: {list(lots_gdf.columns)}")
print(f"\nAddresses columns: {list(addresses_gdf.columns)}")

# Analyze PARCELID in Parcels
print("\n" + "="*80)
print("PARCELS DATASET ANALYSIS")
print("="*80)
print(f"Total Parcels records: {len(parcels_gdf):,}")

parcelid_col = 'PARCELID'
print(f"PARCELID column: '{parcelid_col}'")

null_parcelid = parcels_gdf[parcelid_col].isna()
null_count = null_parcelid.sum()
non_null_count = (~null_parcelid).sum()

print(f"Records with NULL PARCELID: {null_count:,} ({null_count/len(parcels_gdf)*100:.2f}%)")
print(f"Records with non-NULL PARCELID: {non_null_count:,} ({non_null_count/len(parcels_gdf)*100:.2f}%)")

# Get unique non-null PARCELIDs
parcels_valid = parcels_gdf[~null_parcelid].copy()
unique_parcelids = parcels_valid[parcelid_col].unique()
print(f"Unique non-NULL PARCELIDs: {len(unique_parcelids):,}")

# Check for duplicates
duplicate_count = parcels_valid[parcelid_col].duplicated().sum()
print(f"Duplicate PARCELIDs: {duplicate_count:,}")

# Analyze NULL PARCELID records
print("\n" + "="*80)
print("NULL PARCELID INVESTIGATION")
print("="*80)

null_parcels = parcels_gdf[null_parcelid].copy()
print(f"\nTotal records with NULL PARCELID: {len(null_parcels):,}")

# Examine attributes
print("\nAnalyzing attributes of NULL PARCELID records...")
key_fields = ['OW_NAME', 'TYPE_', 'SUBDIVNAME', 'ASSESS_VAL', 'IMP_VAL', 'LAND_VAL', 'TOTAL_VAL', 'GIS_EST_AC']

for field in key_fields:
    if field in null_parcels.columns:
        print(f"\n{field}:")
        if null_parcels[field].dtype == 'object':
            value_counts = null_parcels[field].value_counts(dropna=False).head(5)
            for val, count in value_counts.items():
                val_str = str(val) if pd.notna(val) else "(NULL)"
                print(f"  {val_str}: {count:,}")
        else:
            non_null = null_parcels[field].notna().sum()
            print(f"  Non-null: {non_null:,}, NULL: {null_parcels[field].isna().sum():,}")
            if non_null > 0:
                print(f"  Mean: {null_parcels[field].mean():.2f}, Min: {null_parcels[field].min():.2f}, Max: {null_parcels[field].max():.2f}")

# Show sample records
print("\nSample NULL PARCELID records:")
sample_cols = ['OW_NAME', 'TYPE_', 'SUBDIVNAME', 'TOTAL_VAL', 'GIS_EST_AC']
print(null_parcels[sample_cols].head(3).to_string())

# Spatial Join Analysis
print("\n" + "="*80)
print("SPATIAL JOIN ANALYSIS")
print("="*80)
print("\nNote: Lots and Addresses datasets do not contain PARCELID column.")
print("Performing spatial joins to establish relationships...\n")

# Ensure all datasets have the same CRS
print(f"Parcels CRS: {parcels_gdf.crs}")
print(f"Lots CRS: {lots_gdf.crs}")
print(f"Addresses CRS: {addresses_gdf.crs}")

# Reproject if needed
if lots_gdf.crs != parcels_gdf.crs:
    print("Reprojecting Lots to match Parcels CRS...")
    lots_gdf = lots_gdf.to_crs(parcels_gdf.crs)

if addresses_gdf.crs != parcels_gdf.crs:
    print("Reprojecting Addresses to match Parcels CRS...")
    addresses_gdf = addresses_gdf.to_crs(parcels_gdf.crs)

# Perform spatial joins
print("\n" + "="*80)
print("PARCELS TO LOTS SPATIAL JOIN")
print("="*80)

# Use only valid parcels for spatial joins
print(f"\nPerforming spatial join (Lots within Parcels)...")
print(f"  Joining {len(lots_gdf):,} Lots to {len(parcels_valid):,} valid Parcels...")

# Spatial join: which parcel does each lot fall within?
lots_joined = gpd.sjoin(lots_gdf, parcels_valid[['PARCELID', 'geometry']],
                        how='left', predicate='within')

# Count matches
lots_matched = lots_joined[lots_joined['PARCELID'].notna()]
lots_unmatched = lots_joined[lots_joined['PARCELID'].isna()]

print(f"\nResults:")
print(f"  Lots with matching Parcel: {len(lots_matched):,} ({len(lots_matched)/len(lots_gdf)*100:.2f}%)")
print(f"  Lots without matching Parcel: {len(lots_unmatched):,} ({len(lots_unmatched)/len(lots_gdf)*100:.2f}%)")
print(f"  Unique PARCELIDs matched: {lots_matched['PARCELID'].nunique():,}")

# Check how many unique parcels have at least one lot
parcels_with_lots = parcels_valid[parcels_valid['PARCELID'].isin(lots_matched['PARCELID'])]
lots_coverage = len(parcels_with_lots) / len(parcels_valid) * 100

print(f"\nParcels Coverage:")
print(f"  Parcels with at least one Lot: {len(parcels_with_lots):,} ({lots_coverage:.2f}%)")
print(f"  Parcels without Lots: {len(parcels_valid) - len(parcels_with_lots):,}")

print("\n" + "="*80)
print("PARCELS TO ADDRESSES SPATIAL JOIN")
print("="*80)

print(f"\nPerforming spatial join (Addresses within Parcels)...")
print(f"  Joining {len(addresses_gdf):,} Addresses to {len(parcels_valid):,} valid Parcels...")

# Spatial join: which parcel does each address fall within?
addresses_joined = gpd.sjoin(addresses_gdf, parcels_valid[['PARCELID', 'geometry']],
                             how='left', predicate='within')

# Count matches
addr_matched = addresses_joined[addresses_joined['PARCELID'].notna()]
addr_unmatched = addresses_joined[addresses_joined['PARCELID'].isna()]

print(f"\nResults:")
print(f"  Addresses with matching Parcel: {len(addr_matched):,} ({len(addr_matched)/len(addresses_gdf)*100:.2f}%)")
print(f"  Addresses without matching Parcel: {len(addr_unmatched):,} ({len(addr_unmatched)/len(addresses_gdf)*100:.2f}%)")
print(f"  Unique PARCELIDs matched: {addr_matched['PARCELID'].nunique():,}")

# Check how many unique parcels have at least one address
parcels_with_addresses = parcels_valid[parcels_valid['PARCELID'].isin(addr_matched['PARCELID'])]
addr_coverage = len(parcels_with_addresses) / len(parcels_valid) * 100

print(f"\nParcels Coverage:")
print(f"  Parcels with at least one Address: {len(parcels_with_addresses):,} ({addr_coverage:.2f}%)")
print(f"  Parcels without Addresses: {len(parcels_valid) - len(parcels_with_addresses):,}")

# Orphan records analysis
print("\n" + "="*80)
print("ORPHAN RECORDS ANALYSIS")
print("="*80)

print(f"\nOrphan Lots (not within any valid Parcel):")
print(f"  Count: {len(lots_unmatched):,} ({len(lots_unmatched)/len(lots_gdf)*100:.2f}%)")

if len(lots_unmatched) > 0:
    print("\nSample orphan Lots attributes:")
    sample_cols = ['Lot', 'SubName', 'Block'] if 'SubName' in lots_unmatched.columns else lots_unmatched.columns[:3]
    print(lots_unmatched[sample_cols].head(5).to_string())

print(f"\nOrphan Addresses (not within any valid Parcel):")
print(f"  Count: {len(addr_unmatched):,} ({len(addr_unmatched)/len(addresses_gdf)*100:.2f}%)")

if len(addr_unmatched) > 0:
    print("\nSample orphan Addresses attributes:")
    sample_cols = ['FULL_ADDR', 'CITY', 'ZIP_CODE'] if 'FULL_ADDR' in addr_unmatched.columns else addr_unmatched.columns[:3]
    print(addr_unmatched[sample_cols].head(5).to_string())

# Generate comprehensive report
print("\n" + "="*80)
print("GENERATING MARKDOWN REPORT")
print("="*80)

report_path = DOCS_DIR / "join_validation_report.md"

with open(report_path, 'w') as f:
    f.write("# PARCELID Join Validation Report\n\n")
    f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    f.write("**Objective:** Validate PARCELID as the common identifier across Benton County data sources\n\n")

    f.write("---\n\n")
    f.write("## Executive Summary\n\n")

    f.write("### Key Findings\n\n")
    f.write(f"- **Parcels Dataset:** {len(parcels_gdf):,} total records\n")
    f.write(f"  - Valid PARCELIDs: {len(parcels_valid):,} ({len(parcels_valid)/len(parcels_gdf)*100:.2f}%)\n")
    f.write(f"  - NULL PARCELIDs: {len(null_parcels):,} ({len(null_parcels)/len(parcels_gdf)*100:.2f}%)\n")
    f.write(f"  - Unique valid PARCELIDs: {len(unique_parcelids):,}\n")
    f.write(f"  - Duplicate PARCELIDs: {duplicate_count:,}\n\n")

    f.write(f"- **Lots Dataset:** {len(lots_gdf):,} total records\n")
    f.write(f"  - **NOTE:** Lots dataset does NOT contain PARCELID column\n")
    f.write(f"  - Spatial join coverage: {len(lots_matched):,} records ({len(lots_matched)/len(lots_gdf)*100:.2f}%)\n")
    f.write(f"  - Parcels with Lots: {len(parcels_with_lots):,} ({lots_coverage:.2f}%)\n")
    f.write(f"  - Orphan Lots (no parent Parcel): {len(lots_unmatched):,} ({len(lots_unmatched)/len(lots_gdf)*100:.2f}%)\n\n")

    f.write(f"- **Addresses Dataset:** {len(addresses_gdf):,} total records\n")
    f.write(f"  - **NOTE:** Addresses dataset does NOT contain PARCELID column\n")
    f.write(f"  - Spatial join coverage: {len(addr_matched):,} records ({len(addr_matched)/len(addresses_gdf)*100:.2f}%)\n")
    f.write(f"  - Parcels with Addresses: {len(parcels_with_addresses):,} ({addr_coverage:.2f}%)\n")
    f.write(f"  - Orphan Addresses (no parent Parcel): {len(addr_unmatched):,} ({len(addr_unmatched)/len(addresses_gdf)*100:.2f}%)\n\n")

    f.write("### Critical Discovery\n\n")
    f.write("> **IMPORTANT:** The Lots and Addresses shapefiles do **NOT** contain a PARCELID column. ")
    f.write("These datasets must be joined to Parcels using **spatial joins** (point-in-polygon or within operations), ")
    f.write("not attribute-based joins.\n\n")

    f.write("This has significant implications for ETL pipeline design:\n")
    f.write("- Spatial joins are more computationally expensive than attribute joins\n")
    f.write("- Spatial join results may be non-deterministic at parcel boundaries\n")
    f.write("- Cannot use standard SQL joins; requires spatial database (PostGIS) or in-memory processing\n")
    f.write("- Join performance scales with geometry complexity, not just row count\n\n")

    f.write("---\n\n")
    f.write("## 1. Dataset Overview\n\n")

    f.write("### 1.1 Parcels Dataset\n\n")
    f.write(f"- **File:** `data/raw/Parcels (1)/Parcels.shp`\n")
    f.write(f"- **Total Records:** {len(parcels_gdf):,}\n")
    f.write(f"- **PARCELID Column:** `{parcelid_col}` (EXISTS)\n")
    f.write(f"- **Records with NULL PARCELID:** {len(null_parcels):,} ({len(null_parcels)/len(parcels_gdf)*100:.2f}%)\n")
    f.write(f"- **Records with non-NULL PARCELID:** {len(parcels_valid):,} ({len(parcels_valid)/len(parcels_gdf)*100:.2f}%)\n")
    f.write(f"- **Unique non-NULL PARCELIDs:** {len(unique_parcelids):,}\n")
    f.write(f"- **Duplicate PARCELIDs:** {duplicate_count:,}\n")
    f.write(f"- **CRS:** {parcels_gdf.crs}\n\n")

    if duplicate_count > 0:
        f.write(f"**WARNING:** {duplicate_count:,} duplicate PARCELID values detected! ")
        f.write("PARCELID is NOT a unique identifier.\n\n")

    f.write("### 1.2 Lots Dataset\n\n")
    f.write(f"- **File:** `data/raw/Lots/Lots.shp`\n")
    f.write(f"- **Total Records:** {len(lots_gdf):,}\n")
    f.write(f"- **PARCELID Column:** NOT PRESENT\n")
    f.write(f"- **Available Columns:** {', '.join(lots_gdf.columns.drop('geometry'))}\n")
    f.write(f"- **CRS:** {lots_gdf.crs}\n\n")

    f.write("### 1.3 Addresses Dataset\n\n")
    f.write(f"- **File:** `data/raw/Addresses/Addresses.shp`\n")
    f.write(f"- **Total Records:** {len(addresses_gdf):,}\n")
    f.write(f"- **PARCELID Column:** NOT PRESENT\n")
    f.write(f"- **Available Columns:** {', '.join(addresses_gdf.columns.drop('geometry'))}\n")
    f.write(f"- **CRS:** {addresses_gdf.crs}\n\n")

    f.write("---\n\n")
    f.write("## 2. Spatial Join Coverage Analysis\n\n")

    f.write("Since PARCELID is not present in Lots and Addresses datasets, spatial joins are required ")
    f.write("to establish relationships. The analysis uses **'within'** predicate to find Lots/Addresses ")
    f.write("that fall within Parcel boundaries.\n\n")

    f.write("### 2.1 Parcels to Lots Spatial Join\n\n")
    f.write(f"**Base:** {len(parcels_valid):,} Parcels with non-NULL PARCELID\n\n")
    f.write(f"**Method:** Spatial join using 'within' predicate (Lots within Parcels)\n\n")
    f.write(f"**Results:**\n")
    f.write(f"- Total Lots: {len(lots_gdf):,}\n")
    f.write(f"- Lots matched to Parcels: {len(lots_matched):,} ({len(lots_matched)/len(lots_gdf)*100:.2f}%)\n")
    f.write(f"- Lots without Parcel: {len(lots_unmatched):,} ({len(lots_unmatched)/len(lots_gdf)*100:.2f}%)\n")
    f.write(f"- Unique PARCELIDs with Lots: {lots_matched['PARCELID'].nunique():,}\n\n")

    f.write(f"**Parcels Perspective:**\n")
    f.write(f"- Parcels with at least one Lot: {len(parcels_with_lots):,} ({lots_coverage:.2f}%)\n")
    f.write(f"- Parcels without Lots: {len(parcels_valid) - len(parcels_with_lots):,} ({100-lots_coverage:.2f}%)\n\n")

    coverage_status = "EXCELLENT" if len(lots_matched)/len(lots_gdf)*100 >= 95 else "GOOD" if len(lots_matched)/len(lots_gdf)*100 >= 80 else "MODERATE" if len(lots_matched)/len(lots_gdf)*100 >= 60 else "POOR"
    f.write(f"**Coverage Assessment:** {coverage_status}\n\n")

    f.write("### 2.2 Parcels to Addresses Spatial Join\n\n")
    f.write(f"**Base:** {len(parcels_valid):,} Parcels with non-NULL PARCELID\n\n")
    f.write(f"**Method:** Spatial join using 'within' predicate (Addresses within Parcels)\n\n")
    f.write(f"**Results:**\n")
    f.write(f"- Total Addresses: {len(addresses_gdf):,}\n")
    f.write(f"- Addresses matched to Parcels: {len(addr_matched):,} ({len(addr_matched)/len(addresses_gdf)*100:.2f}%)\n")
    f.write(f"- Addresses without Parcel: {len(addr_unmatched):,} ({len(addr_unmatched)/len(addresses_gdf)*100:.2f}%)\n")
    f.write(f"- Unique PARCELIDs with Addresses: {addr_matched['PARCELID'].nunique():,}\n\n")

    f.write(f"**Parcels Perspective:**\n")
    f.write(f"- Parcels with at least one Address: {len(parcels_with_addresses):,} ({addr_coverage:.2f}%)\n")
    f.write(f"- Parcels without Addresses: {len(parcels_valid) - len(parcels_with_addresses):,} ({100-addr_coverage:.2f}%)\n\n")

    addr_coverage_status = "EXCELLENT" if len(addr_matched)/len(addresses_gdf)*100 >= 95 else "GOOD" if len(addr_matched)/len(addresses_gdf)*100 >= 80 else "MODERATE" if len(addr_matched)/len(addresses_gdf)*100 >= 60 else "POOR"
    f.write(f"**Coverage Assessment:** {addr_coverage_status}\n\n")

    f.write("---\n\n")
    f.write("## 3. Orphan Records Analysis\n\n")

    f.write("### 3.1 Orphan Lots\n\n")
    f.write("Lots records that do not fall within any valid Parcel boundary.\n\n")
    f.write(f"- **Orphan Lots count:** {len(lots_unmatched):,}\n")
    f.write(f"- **Percentage of Lots dataset:** {len(lots_unmatched)/len(lots_gdf)*100:.2f}%\n\n")

    f.write("**Possible Reasons:**\n")
    f.write("1. Geometry misalignment or precision issues\n")
    f.write("2. Lots outside Parcel boundaries (edge cases)\n")
    f.write("3. Lots in areas with NULL PARCELID\n")
    f.write("4. Data synchronization timing differences\n\n")

    if len(lots_unmatched) > 0:
        f.write("**Sample Orphan Lots:**\n\n")
        sample_cols = ['Lot', 'SubName', 'Block'] if 'SubName' in lots_unmatched.columns else list(lots_unmatched.columns[:5])
        sample_cols = [c for c in sample_cols if c != 'geometry']
        sample_df = lots_unmatched[sample_cols].head(10)
        f.write("| " + " | ".join(sample_cols) + " |\n")
        f.write("|" + "|".join(["---" for _ in sample_cols]) + "|\n")
        for _, row in sample_df.iterrows():
            f.write("| " + " | ".join([str(row[c]) if pd.notna(row[c]) else "" for c in sample_cols]) + " |\n")
        f.write("\n")

    f.write("### 3.2 Orphan Addresses\n\n")
    f.write("Address records that do not fall within any valid Parcel boundary.\n\n")
    f.write(f"- **Orphan Addresses count:** {len(addr_unmatched):,}\n")
    f.write(f"- **Percentage of Addresses dataset:** {len(addr_unmatched)/len(addresses_gdf)*100:.2f}%\n\n")

    f.write("**Possible Reasons:**\n")
    f.write("1. Addresses on right-of-way (roads, utilities)\n")
    f.write("2. Addresses in public spaces (parks, government buildings)\n")
    f.write("3. Point location accuracy issues\n")
    f.write("4. Multi-unit buildings with multiple addresses in single parcel\n\n")

    if len(addr_unmatched) > 0:
        f.write("**Sample Orphan Addresses:**\n\n")
        sample_cols = ['FULL_ADDR', 'CITY', 'ZIP_CODE'] if 'FULL_ADDR' in addr_unmatched.columns else list(addr_unmatched.columns[:5])
        sample_cols = [c for c in sample_cols if c != 'geometry']
        sample_df = addr_unmatched[sample_cols].head(10)
        f.write("| " + " | ".join(sample_cols) + " |\n")
        f.write("|" + "|".join(["---" for _ in sample_cols]) + "|\n")
        for _, row in sample_df.iterrows():
            f.write("| " + " | ".join([str(row[c]) if pd.notna(row[c]) else "" for c in sample_cols]) + " |\n")
        f.write("\n")

    f.write("---\n\n")
    f.write("## 4. NULL PARCELID Investigation\n\n")

    f.write(f"### 4.1 Overview\n\n")
    f.write(f"Found **{len(null_parcels):,}** Parcels records with NULL PARCELID ({len(null_parcels)/len(parcels_gdf)*100:.2f}% of total).\n\n")
    f.write("This is a relatively small percentage but worth investigating to understand their nature.\n\n")

    f.write("### 4.2 Attribute Analysis\n\n")
    f.write("Examining other attributes to understand what these NULL PARCELID records represent:\n\n")

    # Analyze key attributes
    for field in key_fields:
        if field in null_parcels.columns:
            f.write(f"#### {field}\n\n")

            if null_parcels[field].dtype == 'object':
                value_counts = null_parcels[field].value_counts(dropna=False).head(10)
                if len(value_counts) > 0:
                    f.write("| Value | Count | Percentage |\n")
                    f.write("|-------|-------|------------|\n")
                    for val, count in value_counts.items():
                        pct = count / len(null_parcels) * 100
                        val_str = str(val)[:50] if pd.notna(val) else "(NULL)"
                        f.write(f"| {val_str} | {count:,} | {pct:.2f}% |\n")
                    f.write("\n")
            else:
                non_null = null_parcels[field].notna().sum()
                null_count_field = null_parcels[field].isna().sum()
                f.write(f"- Non-null values: {non_null:,}\n")
                f.write(f"- NULL values: {null_count_field:,}\n")
                if non_null > 0:
                    f.write(f"- Mean: {null_parcels[field].mean():.2f}\n")
                    f.write(f"- Median: {null_parcels[field].median():.2f}\n")
                    f.write(f"- Min: {null_parcels[field].min():.2f}\n")
                    f.write(f"- Max: {null_parcels[field].max():.2f}\n")
                f.write("\n")

    f.write("### 4.3 Possible Explanations\n\n")
    f.write("Based on the attribute analysis, NULL PARCELID records may represent:\n\n")
    f.write("1. **Right-of-Way (ROW):** Public roads, utilities, or easements\n")
    f.write("2. **Public Lands:** Parks, government property, or common areas\n")
    f.write("3. **Unplatted Land:** Parcels not yet assigned formal identifiers\n")
    f.write("4. **Pending Development:** New subdivisions awaiting final platting\n")
    f.write("5. **Water Features:** Rivers, lakes, or other water bodies\n")
    f.write("6. **Data Quality Issues:** Records pending cleanup or validation\n\n")

    f.write("**Recommendation:** Review a sample of NULL PARCELID records with domain experts ")
    f.write("to determine appropriate handling strategy. Consider:\n")
    f.write("- Assigning special PARCELID codes (e.g., 'ROW-001', 'PARK-001')\n")
    f.write("- Flagging for exclusion from certain analyses\n")
    f.write("- Spatial join with alternative identifier datasets\n\n")

    f.write("---\n\n")
    f.write("## 5. Data Quality Recommendations\n\n")

    f.write("### 5.1 PARCELID as Primary Key\n\n")

    if duplicate_count > 0:
        f.write(f"**CRITICAL ISSUE:** Found {duplicate_count:,} duplicate PARCELID values in Parcels dataset!\n\n")
        f.write("PARCELID is **NOT** a suitable primary key due to duplicates. Investigate:\n")
        f.write("- Are duplicates intentional (e.g., condos, multiple owners)?\n")
        f.write("- Should a composite key be used instead?\n")
        f.write("- Consider creating a surrogate key (auto-increment ID)\n\n")

        # Show sample duplicates
        dup_parcelids = parcels_valid[parcels_valid[parcelid_col].duplicated(keep=False)][parcelid_col].value_counts().head(5)
        f.write("**Top Duplicate PARCELIDs:**\n\n")
        f.write("| PARCELID | Occurrence Count |\n")
        f.write("|----------|------------------|\n")
        for pid, count in dup_parcelids.items():
            f.write(f"| {pid} | {count} |\n")
        f.write("\n")
    else:
        f.write("**GOOD:** All non-NULL PARCELIDs are unique in the Parcels dataset.\n\n")
        f.write("PARCELID can serve as a primary key for non-NULL records.\n\n")

    f.write("### 5.2 Join Strategy Recommendations\n\n")
    f.write("#### Attribute-Based Joins (Not Applicable)\n\n")
    f.write("Standard SQL joins on PARCELID **cannot** be used for Lots and Addresses datasets ")
    f.write("since they lack PARCELID columns.\n\n")

    f.write("#### Spatial Join Approach (Required)\n\n")
    f.write("```python\n")
    f.write("# Load datasets\n")
    f.write("parcels = gpd.read_file('Parcels.shp')\n")
    f.write("lots = gpd.read_file('Lots.shp')\n")
    f.write("addresses = gpd.read_file('Addresses.shp')\n\n")
    f.write("# Ensure same CRS\n")
    f.write("lots = lots.to_crs(parcels.crs)\n")
    f.write("addresses = addresses.to_crs(parcels.crs)\n\n")
    f.write("# Spatial joins\n")
    f.write("lots_enriched = gpd.sjoin(lots, parcels[['PARCELID', 'geometry']], \n")
    f.write("                          how='left', predicate='within')\n\n")
    f.write("addresses_enriched = gpd.sjoin(addresses, parcels[['PARCELID', 'geometry']], \n")
    f.write("                                how='left', predicate='within')\n")
    f.write("```\n\n")

    f.write("#### Performance Considerations\n\n")
    f.write("Spatial joins are computationally expensive. For large datasets:\n\n")
    f.write("1. **Use Spatial Indexing:** Ensure .shp files have .sbn/.sbx spatial index files\n")
    f.write("2. **Database Approach:** Load into PostGIS with spatial indexes\n")
    f.write("   ```sql\n")
    f.write("   CREATE INDEX parcels_geom_idx ON parcels USING GIST(geometry);\n")
    f.write("   CREATE INDEX lots_geom_idx ON lots USING GIST(geometry);\n")
    f.write("   ```\n")
    f.write("3. **Chunking:** Process data in batches to manage memory\n")
    f.write("4. **Caching:** Persist join results to avoid repeated spatial operations\n")
    f.write("5. **Simplification:** Consider simplifying geometries for faster joins\n\n")

    f.write("### 5.3 ETL Pipeline Design\n\n")

    f.write("#### Airflow DAG Structure\n\n")
    f.write("```python\n")
    f.write("from airflow import DAG\n")
    f.write("from airflow.operators.python import PythonOperator\n")
    f.write("from datetime import datetime, timedelta\n\n")
    f.write("default_args = {\n")
    f.write("    'owner': 'data-engineering',\n")
    f.write("    'depends_on_past': False,\n")
    f.write("    'start_date': datetime(2025, 1, 1),\n")
    f.write("    'email_on_failure': True,\n")
    f.write("    'retries': 2,\n")
    f.write("    'retry_delay': timedelta(minutes=5)\n")
    f.write("}\n\n")
    f.write("dag = DAG(\n")
    f.write("    'benton_county_spatial_etl',\n")
    f.write("    default_args=default_args,\n")
    f.write("    schedule_interval='0 2 * * *',  # Daily at 2 AM\n")
    f.write("    catchup=False\n")
    f.write(")\n\n")
    f.write("# Task 1: Load and validate Parcels\n")
    f.write("load_parcels = PythonOperator(\n")
    f.write("    task_id='load_parcels',\n")
    f.write("    python_callable=load_and_validate_parcels,\n")
    f.write("    dag=dag\n")
    f.write(")\n\n")
    f.write("# Task 2: Spatial join Lots to Parcels\n")
    f.write("enrich_lots = PythonOperator(\n")
    f.write("    task_id='enrich_lots',\n")
    f.write("    python_callable=spatial_join_lots,\n")
    f.write("    dag=dag\n")
    f.write(")\n\n")
    f.write("# Task 3: Spatial join Addresses to Parcels\n")
    f.write("enrich_addresses = PythonOperator(\n")
    f.write("    task_id='enrich_addresses',\n")
    f.write("    python_callable=spatial_join_addresses,\n")
    f.write("    dag=dag\n")
    f.write(")\n\n")
    f.write("# Task 4: Data quality checks\n")
    f.write("quality_checks = PythonOperator(\n")
    f.write("    task_id='quality_checks',\n")
    f.write("    python_callable=run_quality_checks,\n")
    f.write("    dag=dag\n")
    f.write(")\n\n")
    f.write("load_parcels >> [enrich_lots, enrich_addresses] >> quality_checks\n")
    f.write("```\n\n")

    f.write("### 5.4 Data Quality Monitoring\n\n")

    f.write("Implement automated monitoring for:\n\n")

    f.write("**Key Metrics:**\n")
    f.write("1. NULL PARCELID percentage (alert if > 1%)\n")
    f.write(f"2. Lots spatial join coverage (alert if < {len(lots_matched)/len(lots_gdf)*100:.0f}%)\n")
    f.write(f"3. Addresses spatial join coverage (alert if < {len(addr_matched)/len(addresses_gdf)*100:.0f}%)\n")
    f.write("4. Orphan record counts (alert if increasing trend)\n")
    f.write("5. Duplicate PARCELID count (alert if any)\n\n")

    f.write("**Sample Monitoring Query (PostGIS):**\n")
    f.write("```sql\n")
    f.write("-- Monitor NULL PARCELID rate\n")
    f.write("SELECT \n")
    f.write("    COUNT(*) as total_parcels,\n")
    f.write("    COUNT(parcelid) as valid_parcelids,\n")
    f.write("    COUNT(*) - COUNT(parcelid) as null_parcelids,\n")
    f.write("    ROUND(100.0 * (COUNT(*) - COUNT(parcelid)) / COUNT(*), 2) as null_pct\n")
    f.write("FROM parcels;\n\n")
    f.write("-- Monitor spatial join coverage\n")
    f.write("SELECT \n")
    f.write("    COUNT(l.*) as total_lots,\n")
    f.write("    COUNT(p.parcelid) as matched_lots,\n")
    f.write("    ROUND(100.0 * COUNT(p.parcelid) / COUNT(l.*), 2) as coverage_pct\n")
    f.write("FROM lots l\n")
    f.write("LEFT JOIN parcels p ON ST_Within(l.geometry, p.geometry);\n")
    f.write("```\n\n")

    f.write("### 5.5 Data Governance\n\n")
    f.write("1. **Establish Primary Source:** Confirm Parcels dataset is authoritative for PARCELID\n")
    f.write("2. **Document Join Logic:** Clearly document that Lots/Addresses require spatial joins\n")
    f.write("3. **NULL Handling Policy:** Define business rules for NULL PARCELID records\n")
    f.write("4. **Geometry Quality:** Implement topology validation (no gaps, overlaps)\n")
    f.write("5. **Data Lineage:** Document data refresh schedules and dependencies\n")
    f.write("6. **SLA Definition:** Define acceptable join coverage thresholds\n")
    f.write("7. **Change Management:** Track schema changes and geometry updates\n\n")

    f.write("---\n\n")
    f.write("## 6. Summary Statistics\n\n")

    f.write("| Metric | Value |\n")
    f.write("|--------|-------|\n")
    f.write(f"| Total Parcels | {len(parcels_gdf):,} |\n")
    f.write(f"| Valid PARCELIDs in Parcels | {len(parcels_valid):,} |\n")
    f.write(f"| Unique PARCELIDs | {len(unique_parcelids):,} |\n")
    f.write(f"| NULL PARCELIDs in Parcels | {len(null_parcels):,} ({len(null_parcels)/len(parcels_gdf)*100:.2f}%) |\n")
    f.write(f"| Duplicate PARCELIDs | {duplicate_count:,} |\n")
    f.write(f"| | |\n")
    f.write(f"| Total Lots | {len(lots_gdf):,} |\n")
    f.write(f"| Lots Matched (Spatial Join) | {len(lots_matched):,} ({len(lots_matched)/len(lots_gdf)*100:.2f}%) |\n")
    f.write(f"| Orphan Lots | {len(lots_unmatched):,} ({len(lots_unmatched)/len(lots_gdf)*100:.2f}%) |\n")
    f.write(f"| Parcels with Lots | {len(parcels_with_lots):,} ({lots_coverage:.2f}%) |\n")
    f.write(f"| | |\n")
    f.write(f"| Total Addresses | {len(addresses_gdf):,} |\n")
    f.write(f"| Addresses Matched (Spatial Join) | {len(addr_matched):,} ({len(addr_matched)/len(addresses_gdf)*100:.2f}%) |\n")
    f.write(f"| Orphan Addresses | {len(addr_unmatched):,} ({len(addr_unmatched)/len(addresses_gdf)*100:.2f}%) |\n")
    f.write(f"| Parcels with Addresses | {len(parcels_with_addresses):,} ({addr_coverage:.2f}%) |\n")

    f.write("\n---\n\n")
    f.write("## 7. Conclusion\n\n")

    f.write("### Key Takeaways\n\n")
    f.write("1. **PARCELID is ONLY in Parcels dataset** - Lots and Addresses require spatial joins\n")
    f.write("2. **598 NULL PARCELIDs** found in Parcels (0.34%) - manageable but needs investigation\n")
    if duplicate_count > 0:
        f.write(f"3. **{duplicate_count:,} Duplicate PARCELIDs** - CRITICAL issue affecting data integrity\n")
    else:
        f.write("3. **No duplicate PARCELIDs** - PARCELID can serve as unique identifier\n")
    f.write(f"4. **Spatial join coverage** - Lots: {len(lots_matched)/len(lots_gdf)*100:.1f}%, Addresses: {len(addr_matched)/len(addresses_gdf)*100:.1f}%\n")
    f.write(f"5. **Orphan records exist** - {len(lots_unmatched):,} Lots and {len(addr_unmatched):,} Addresses without Parcels\n\n")

    f.write("### Next Steps\n\n")
    f.write("1. **Investigate duplicate PARCELIDs** - Understand root cause and remediation\n")
    f.write("2. **Review NULL PARCELID records** - Classify and assign handling strategy\n")
    f.write("3. **Analyze orphan records** - Determine if data quality issue or expected\n")
    f.write("4. **Design ETL pipeline** - Implement spatial join logic with performance optimization\n")
    f.write("5. **Set up monitoring** - Track join coverage and data quality metrics\n")
    f.write("6. **Document data model** - Create clear documentation for downstream consumers\n\n")

    f.write("---\n\n")
    f.write("## Appendix: Column Details\n\n")

    f.write("### Parcels Columns\n")
    f.write(f"```\n{list(parcels_gdf.columns)}\n```\n\n")

    f.write("### Lots Columns\n")
    f.write(f"```\n{list(lots_gdf.columns)}\n```\n\n")

    f.write("### Addresses Columns\n")
    f.write(f"```\n{list(addresses_gdf.columns)}\n```\n\n")

print(f"\nReport saved to: {report_path}")
print(f"Report size: {report_path.stat().st_size:,} bytes")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
