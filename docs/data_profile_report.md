# GIS Data Profile Report

Generated: 2025-12-07 22:41:54

---

## 1. Parcels.shp

**File Path:** `C:\taxdown\data\raw\Parcels (1)\Parcels.shp`

### Record Count

**Total Records:** 173,743

### Coordinate Reference System (CRS)

```
EPSG:3433
```

### Column Information

| Column Name | Data Type |
|-------------|-----------|
| PARCELID | object |
| ACRE_AREA | float64 |
| OW_NAME | object |
| OW_ADD | object |
| PH_ADD | object |
| TYPE_ | object |
| ASSESS_VAL | int64 |
| IMP_VAL | int64 |
| LAND_VAL | int64 |
| TOTAL_VAL | int64 |
| S_T_R | object |
| SCHL_CODE | object |
| GIS_EST_AC | float64 |
| SUBDIVNAME | object |
| Shape_Leng | float64 |
| Shape_Area | float64 |
| geometry | geometry |

### Primary Key / Unique Identifier

**No unique identifier field found.**

*Note: No single field contains unique non-null values for all records.*

### Null Value Analysis

| Column Name | Null Count | Percentage |
|-------------|------------|------------|
| PARCELID | 598 | 0.34% |
| OW_NAME | 2,498 | 1.44% |
| OW_ADD | 2,559 | 1.47% |
| PH_ADD | 5,997 | 3.45% |
| TYPE_ | 2,498 | 1.44% |
| S_T_R | 2,498 | 1.44% |
| SCHL_CODE | 2,498 | 1.44% |
| SUBDIVNAME | 2,498 | 1.44% |

### Sample Records (3 records, geometry excluded)

```
  PARCELID  ACRE_AREA OW_NAME OW_ADD PH_ADD TYPE_  ASSESS_VAL  IMP_VAL  LAND_VAL  TOTAL_VAL S_T_R SCHL_CODE  GIS_EST_AC SUBDIVNAME   Shape_Leng     Shape_Area
0     None        0.0    None   None   None  None           0        0         0          0  None      None     5.32296       None  3052.197888  231867.980022
1     None        0.0    None   None   None  None           0        0         0          0  None      None     0.33975       None   764.225952   14799.634176
2     None        0.0    None   None   None  None           0        0         0          0  None      None     2.80477       None  4727.259611  122185.600841
```

---

## 2. Subdivisions.shp

**File Path:** `C:\taxdown\data\raw\Subdivisions\Subdivisions.shp`

### Record Count

**Total Records:** 4,041

### Coordinate Reference System (CRS)

```
EPSG:3433
```

### Column Information

| Column Name | Data Type |
|-------------|-----------|
| NAME | object |
| CAMA_Name | object |
| Shape_Leng | float64 |
| Shape_Area | float64 |
| geometry | geometry |

### Primary Key / Unique Identifier

**No unique identifier field found.**

*Note: No single field contains unique non-null values for all records.*

### Null Value Analysis

| Column Name | Null Count | Percentage |
|-------------|------------|------------|
| NAME | 1 | 0.02% |
| CAMA_Name | 1 | 0.02% |

### Sample Records (3 records, geometry excluded)

```
                  NAME                   CAMA_Name   Shape_Leng    Shape_Area
0   MCNAIR SUBDIVISION   MCNAIR SUB-SILOAM SPRINGS  1049.328611  6.819735e+04
1     COLLEGE ADDITION  COLLEGE ADD-SILOAM SPRINGS  5030.659134  1.482615e+06
2  PETTY'S SUBDIVISION  PETTY'S SUB-SILOAM SPRINGS  2995.452308  1.808757e+05
```

---

## 3. Lots.shp

**File Path:** `C:\taxdown\data\raw\Lots\Lots.shp`

### Record Count

**Total Records:** 150,764

### Coordinate Reference System (CRS)

```
EPSG:3433
```

### Column Information

| Column Name | Data Type |
|-------------|-----------|
| TYPE | object |
| Lot | object |
| SubName | object |
| Block | object |
| Shape_Leng | float64 |
| Shape_Area | float64 |
| geometry | geometry |

### Primary Key / Unique Identifier

**No unique identifier field found.**

*Note: No single field contains unique non-null values for all records.*

### Null Value Analysis

| Column Name | Null Count | Percentage |
|-------------|------------|------------|
| TYPE | 5 | 0.00% |
| Lot | 7,144 | 4.74% |
| SubName | 6,333 | 4.20% |
| Block | 78,171 | 51.85% |

### Sample Records (3 records, geometry excluded)

```
  TYPE   Lot SubName Block   Shape_Leng     Shape_Area
0  LOT  None    None  None  1861.388200  178003.282538
1  LOT  None    None  None  2552.891322  131162.334249
2  LOT  None    None  None   840.727242    3385.188401
```

---

## 4. Addresses.shp

**File Path:** `C:\taxdown\data\raw\Addresses\Addresses.shp`

### Record Count

**Total Records:** 164,759

### Coordinate Reference System (CRS)

```
EPSG:3433
```

### Column Information

| Column Name | Data Type |
|-------------|-----------|
| ADDR_NUM | object |
| PRE_DIR | object |
| ROAD_NAME | object |
| TYPE | object |
| SUF_DIR | object |
| FULL_ADDR | object |
| UNIT_APT | object |
| CITY | object |
| ZIP_CODE | object |
| CLASSIFICA | object |
| City_Zip | object |
| geometry | geometry |

### Primary Key / Unique Identifier

**No unique identifier field found.**

*Note: No single field contains unique non-null values for all records.*

### Null Value Analysis

| Column Name | Null Count | Percentage |
|-------------|------------|------------|
| PRE_DIR | 79,657 | 48.35% |
| TYPE | 1,671 | 1.01% |
| SUF_DIR | 163,426 | 99.19% |
| UNIT_APT | 129,629 | 78.68% |
| CITY | 93 | 0.06% |
| CLASSIFICA | 197 | 0.12% |
| City_Zip | 380 | 0.23% |

### Sample Records (3 records, geometry excluded)

```
  ADDR_NUM PRE_DIR    ROAD_NAME  TYPE SUF_DIR             FULL_ADDR UNIT_APT           CITY ZIP_CODE   CLASSIFICA        City_Zip
0     1400      SE       WALTON  BLVD    None   1400 SE WALTON BLVD       32    BENTONVILLE    72712   COMMERCIAL     BENTONVILLE
1    18755    None  SHADY GROVE    RD    None  18755 SHADY GROVE RD     None  BENTON COUNTY    72761  RESIDENTIAL  SILOAM SPRINGS
2    14387    None    FAIRMOUNT    RD    None    14387 FAIRMOUNT RD     None  BENTON COUNTY    72761  RESIDENTIAL  SILOAM SPRINGS
```

---

## 5. Cities.shp

**File Path:** `C:\taxdown\data\raw\Cities\Cities.shp`

### Record Count

**Total Records:** 20

### Coordinate Reference System (CRS)

```
EPSG:3433
```

### Column Information

| Column Name | Data Type |
|-------------|-----------|
| CITY_NAME | object |
| Shape_Leng | float64 |
| Shape_Area | float64 |
| geometry | geometry |

### Primary Key / Unique Identifier

**Identified Primary Key Candidate(s):** CITY_NAME, Shape_Leng, Shape_Area

*Note: These fields have unique values for all records with no nulls.*

### Null Value Analysis

**No null values found in any fields.**

### Sample Records (3 records, geometry excluded)

```
  CITY_NAME    Shape_Leng    Shape_Area
0   GATEWAY  62517.373301  1.820093e+08
1     AVOCA  40691.533905  5.385218e+07
2   DECATUR  89752.428827  1.382240e+08
```

---

## 6. Arkansas.geojson

**File Path:** `C:\taxdown\data\raw\Arkansas.geojson\Arkansas.geojson`

### Record Count

**Total Records:** 1,571,198

### Coordinate Reference System (CRS)

```
EPSG:4326
```

### Column Information

| Column Name | Data Type |
|-------------|-----------|
| release | int32 |
| capture_dates_range | object |
| geometry | geometry |

### Primary Key / Unique Identifier

**No unique identifier field found.**

*Note: No single field contains unique non-null values for all records.*

### Null Value Analysis

**No null values found in any fields.**

### Sample Records (3 records, geometry excluded)

```
   release capture_dates_range
0        2  9/9/2019-9/15/2019
1        2  9/9/2019-9/15/2019
2        2  9/9/2019-9/15/2019
```

---
