# Liver Biopsy Episode Cost Notebooks — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a series of six Quarto notebooks that assess variance and reliability of MedStar hospital price-transparency data for modeling the full episode cost of a liver biopsy testing for transplanted organ rejection, benchmarked against CMS MPFS national rates.

**Architecture:** Linear pipeline of numbered .qmd notebooks sharing a `_common.py` module for CPT code definitions, DuckDB connection, and column mappings. Intermediate data flows as Parquet files in `data/intermediate/`. Each notebook reads upstream Parquet outputs and either produces analysis or writes its own Parquet for downstream consumption.

**Tech Stack:** Python 3.12+, DuckDB (query engine), Polars (DataFrames), matplotlib (visualization), Quarto (notebook rendering), pytest (unit tests for shared module)

---

## Task 1: Project Setup — Dependencies, Directories, and Shared Module

**Files:**
- Modify: `pyproject.toml`
- Create: `_common.py`
- Create: `tests/test_common.py`
- Create: `data/intermediate/` (directory)
- Create: `data/cms/` (directory)

- [ ] **Step 1: Add dependencies to pyproject.toml**

Add `matplotlib` and `pytest` to the project. Edit `pyproject.toml`:

```toml
[project]
name = "diagnostic-costs"
version = "0.1.0"
description = ""
authors = [
    {name = "Matthew Lyn",email = "lynma01@gmail.com"}
]
readme = "README.md"
requires-python = ">=3.12,<4"
dependencies = [
    "polars (>=1.26.0,<2.0.0)",
    "duckdb (>=1.2.1,<2.0.0)",
    "duckdb-engine (>=0.15.0,<0.16.0)",
    "ipykernel (>=6.29.5,<7.0.0)",
    "matplotlib (>=3.9.0,<4.0.0)",
]

[tool.pytest.ini_options]
testpaths = ["tests"]

[build-system]
requires = ["poetry-core>=2.0.0,<3.0.0"]
build-backend = "poetry.core.masonry.api"
```

- [ ] **Step 2: Install dependencies and verify prerequisites**

```bash
poetry add --group dev pytest
poetry install
quarto --version
python -c "import duckdb, polars, matplotlib; print('OK')"
```

Expected: poetry resolves, quarto prints a version (must be installed system-level), Python import succeeds.

- [ ] **Step 3: Create directories**

```bash
mkdir -p data/intermediate data/cms tests
```

- [ ] **Step 4: Write `_common.py`**

```python
from pathlib import Path

import duckdb
import polars as pl

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
INTERMEDIATE_DIR = DATA_DIR / "intermediate"
CMS_DIR = DATA_DIR / "cms"

MEDSTAR_HOSPITALS: dict[str, str] = {
    "franklin_square": "https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/520608007_medstarfranklinsquaremedicalcenter_standardcharges.csv",
    "georgetown_univ": "https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/522218584_medstargeorgetownuniversityhospital_standardcharges.csv",
    "good_samaritan": "https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/520591607_medstargoodsamaritan_standardcharges.csv",
    "harbor_hosp": "https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/520491660_medstarharborhospital_standardcharges.csv",
    "montgomery_med": "https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/520646893_medstarmontgomerymedicalcenter_standardcharges.csv",
    "national_rehab": "https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/521369749_medstarnationalrehabilitationhospital_standardcharges.csv",
    "s_maryland": "https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/460726303_medstarsouthernmarylandhospitalcenter_standardcharges.csv",
    "mary_hosp": "https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/520619006_medstarstmaryshospital_standardcharges.csv",
    "union_memorial": "https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/520591685_medstarunionmemorialhospital_standardcharges.csv",
    "washington_hosp_center": "https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/521272129_medstarwashingtonhospitalcenter_standardcharges.csv",
}

COLUMN_MAP: dict[str, str] = {
    "code|3": "cpt_code",
    "code|3|type": "cpt_code_type",
    "code|1": "drg_code",
    "code|1|type": "drg_code_type",
    "standard_charge|gross": "charge_gross",
    "standard_charge|min": "charge_min",
    "standard_charge|max": "charge_max",
    "standard_charge|discounted_cash": "charge_discounted",
}

CHARGE_COLS: list[str] = [
    "charge_gross",
    "charge_min",
    "charge_max",
    "charge_discounted",
]

_CODE_GROUPS: dict[str, dict] = {
    "office_em": {
        "codes": [99202, 99203, 99204, 99205, 99211, 99212, 99213, 99214, 99215],
        "setting": "both",
    },
    "initial_hospital_care": {
        "codes": [99221, 99222, 99223],
        "setting": "inpatient",
    },
    "emergency_dept": {
        "codes": [99281, 99282, 99283, 99284, 99285],
        "setting": "inpatient",
    },
    "critical_care": {
        "codes": [99291],
        "setting": "inpatient",
    },
    "prolonged_services": {
        "codes": [99345, 99358, 99417],
        "setting": "both",
    },
    "interprofessional_consult": {
        "codes": [99366, 99367, 99368],
        "setting": "inpatient",
    },
    "preventive_medicine": {
        "codes": [99384, 99385, 99386, 99387, 99394, 99395, 99396, 99397, 99399],
        "setting": "both",
    },
    "counseling": {
        "codes": [99406, 99407],
        "setting": "both",
    },
    "unlisted_preventive": {
        "codes": [99429],
        "setting": "both",
    },
    "care_management": {
        "codes": [99439, 99441, 99442, 99443],
        "setting": "both",
    },
    "neonatal_newborn": {
        "codes": [99461, 99463, 99464, 99465],
        "setting": "inpatient",
    },
    "complex_chronic_care": {
        "codes": [99480, 99483, 99484],
        "setting": "inpatient",
    },
    "transitional_remote_care": {
        "codes": [99490, 99491, 99492, 99493, 99494, 99495, 99496, 99498],
        "setting": "both",
    },
    "infusion": {
        "codes": [96360, 96361, 96365, 96366, 96367, 96368],
        "setting": "both",
    },
    "wound_repair": {
        "codes": [12031],
        "setting": "both",
    },
    "nerve_block": {
        "codes": [64530],
        "setting": "both",
    },
    "biopsy": {
        "codes": [47000],
        "setting": "inpatient",
    },
}

EPISODE_FREQUENCIES: dict[str, dict] = {
    "initial_hospital_care": {"code": 99223, "qty": 1},
    "office_followup": {"code": 99214, "qty": 1},
    "biopsy": {"code": 47000, "qty": 1},
    "nerve_block": {"code": 64530, "qty": 1},
    "wound_repair": {"code": 12031, "qty": 1},
    "infusion_initial": {"code": 96365, "qty": 1},
    "infusion_additional": {"code": 96366, "qty": 1},
}


def get_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect()


def build_episode_codes_df() -> pl.DataFrame:
    rows: list[dict] = []
    for role, group in _CODE_GROUPS.items():
        for code in group["codes"]:
            rows.append(
                {
                    "cpt_code": str(code),
                    "clinical_role": role,
                    "setting": group["setting"],
                }
            )
    return pl.DataFrame(rows, schema={"cpt_code": pl.Utf8, "clinical_role": pl.Utf8, "setting": pl.Utf8})


def standardize_columns(df: pl.DataFrame) -> pl.DataFrame:
    rename = {k: v for k, v in COLUMN_MAP.items() if k in df.columns}
    return df.rename(rename)
```

- [ ] **Step 5: Write `tests/test_common.py`**

```python
import polars as pl
import _common as C


def test_medstar_hospitals_has_10_entries():
    assert len(C.MEDSTAR_HOSPITALS) == 10


def test_all_hospital_urls_are_https():
    for name, url in C.MEDSTAR_HOSPITALS.items():
        assert url.startswith("https://"), f"{name} URL is not HTTPS"


def test_column_map_covers_charge_columns():
    mapped_values = set(C.COLUMN_MAP.values())
    for col in C.CHARGE_COLS:
        assert col in mapped_values, f"{col} not in COLUMN_MAP values"


def test_code_groups_all_have_codes():
    for role, group in C._CODE_GROUPS.items():
        assert len(group["codes"]) > 0, f"{role} has no codes"
        assert group["setting"] in ("inpatient", "outpatient", "both"), f"{role} bad setting"


def test_biopsy_code_present():
    all_codes = []
    for group in C._CODE_GROUPS.values():
        all_codes.extend(group["codes"])
    assert 47000 in all_codes


def test_build_episode_codes_df_schema():
    df = C.build_episode_codes_df()
    assert df.columns == ["cpt_code", "clinical_role", "setting"]
    assert df.shape[0] > 60


def test_build_episode_codes_df_no_duplicates():
    df = C.build_episode_codes_df()
    assert df.shape[0] == df.unique().shape[0]


def test_standardize_columns_renames():
    df = pl.DataFrame({"code|3": ["47000"], "standard_charge|gross": [1500.0], "other_col": ["x"]})
    result = C.standardize_columns(df)
    assert "cpt_code" in result.columns
    assert "charge_gross" in result.columns
    assert "other_col" in result.columns
    assert "code|3" not in result.columns


def test_get_connection():
    con = C.get_connection()
    result = con.sql("SELECT 1 AS n").pl()
    assert result["n"][0] == 1
    con.close()


def test_episode_frequencies_codes_exist_in_groups():
    all_codes = set()
    for group in C._CODE_GROUPS.values():
        all_codes.update(group["codes"])
    for key, freq in C.EPISODE_FREQUENCIES.items():
        assert freq["code"] in all_codes, f"Frequency code {freq['code']} for '{key}' not in code groups"
        assert freq["qty"] >= 1
```

- [ ] **Step 6: Run tests**

```bash
python -m pytest tests/test_common.py -v
```

Expected: all 11 tests pass.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml _common.py tests/test_common.py
git commit -m "add shared module with CPT codes, hospital registry, and tests"
```

---

## Task 2: `00_setup.qmd` — Environment & Code Definitions

**Files:**
- Create: `00_setup.qmd`

**Depends on:** Task 1 (`_common.py` exists)

- [ ] **Step 1: Write `00_setup.qmd`**

```markdown
---
title: "00 — Environment & Code Definitions"
description: |
  Validates the Python environment, defines the full CPT episode bundle for
  liver biopsy rejection testing, and writes episode_codes.parquet for
  downstream notebooks.
dependencies: []
format: html
jupyter: python3
---

## Environment Check

```{python}
import importlib.metadata
import shutil

for pkg in ["polars", "duckdb", "matplotlib"]:
    print(f"{pkg}: {importlib.metadata.version(pkg)}")

quarto_path = shutil.which("quarto")
assert quarto_path is not None, "Quarto CLI not found on PATH"
print(f"quarto: {quarto_path}")
```

## Episode CPT Code Bundle

This project models the **full episode cost** for a liver biopsy testing for
transplanted organ rejection. The episode includes consult, infusion,
procedure, and follow-up codes across inpatient and outpatient settings.

The codes below were provided as the episode definition. Some categories
(neonatal, preventive medicine) may not appear in hospital data for this
procedure — downstream notebooks will surface those gaps.

```{python}
from _common import build_episode_codes_df, INTERMEDIATE_DIR, _CODE_GROUPS

episode_codes = build_episode_codes_df()
print(f"Total episode codes: {episode_codes.shape[0]}")
print(f"Clinical roles: {episode_codes['clinical_role'].n_unique()}")
print()

for role in episode_codes["clinical_role"].unique().sort().to_list():
    subset = episode_codes.filter(episode_codes["clinical_role"] == role)
    codes = subset["cpt_code"].to_list()
    setting = subset["setting"][0]
    print(f"  {role} ({setting}): {', '.join(codes)}")
```

## Write Episode Codes to Parquet

```{python}
INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
out_path = INTERMEDIATE_DIR / "episode_codes.parquet"
episode_codes.write_parquet(out_path)
print(f"Wrote {episode_codes.shape[0]} rows to {out_path}")
```

## DuckDB Smoke Test

```{python}
from _common import get_connection

con = get_connection()
result = con.sql("SELECT 42 AS answer").pl()
assert result["answer"][0] == 42
print("DuckDB connection OK")
con.close()
```
```

- [ ] **Step 2: Render and verify**

```bash
quarto render 00_setup.qmd
```

Expected: renders to `00_setup.html` without errors. Check that `data/intermediate/episode_codes.parquet` exists.

```bash
python -c "import polars as pl; df = pl.read_parquet('data/intermediate/episode_codes.parquet'); print(df.shape); print(df.head(5))"
```

Expected: shape is (N, 3) where N > 60, columns are `cpt_code`, `clinical_role`, `setting`.

- [ ] **Step 3: Commit**

```bash
git add 00_setup.qmd
git commit -m "add 00_setup notebook: environment check and episode code definitions"
```

---

## Task 3: `01_ingest.qmd` — Data Ingestion

**Files:**
- Create: `01_ingest.qmd`

**Depends on:** Task 2 (`data/intermediate/episode_codes.parquet` exists)

**CMS MPFS prerequisite:** Before running this notebook, download the CMS Physician Fee Schedule national payment file (CSV) from <https://www.cms.gov/medicare/payment/fee-schedules/physician/look-up-tool> and place it at `data/cms/mpfs_national.csv`. The notebook will check for this file and provide instructions if missing.

- [ ] **Step 1: Write `01_ingest.qmd`**

```markdown
---
title: "01 — Data Ingestion"
description: |
  Loads MedStar hospital price transparency CSVs and CMS MPFS national data,
  filters to episode-relevant CPT codes, standardizes columns, and writes
  Parquet intermediates.
dependencies:
  - data/intermediate/episode_codes.parquet
format: html
jupyter: python3
---

## Load Episode Codes

```{python}
import polars as pl
from _common import (
    INTERMEDIATE_DIR, CMS_DIR, MEDSTAR_HOSPITALS, COLUMN_MAP,
    CHARGE_COLS, get_connection, standardize_columns,
)

episode_codes = pl.read_parquet(INTERMEDIATE_DIR / "episode_codes.parquet")
episode_cpt_set = set(episode_codes["cpt_code"].to_list())
print(f"Filtering to {len(episode_cpt_set)} episode CPT codes")
```

## Load MedStar Hospital Data

Each hospital's price transparency CSV is read directly from the MedStar URL.
We union all hospitals, filter to episode-relevant CPT codes, and standardize
column names.

```{python}
con = get_connection()

cte_parts = []
for name, url in MEDSTAR_HOSPITALS.items():
    cte_parts.append(f"""
    {name} AS (
        SELECT
            description,
            "code|1", "code|1|type",
            "code|3", "code|3|type",
            setting, billing_class,
            "standard_charge|gross",
            "standard_charge|min",
            "standard_charge|max",
            "standard_charge|discounted_cash",
            '{name}' AS hosp_name
        FROM read_csv('{url}', skip=2, sample_size=-1)
    )""")

union_parts = " UNION ALL ".join(
    f"SELECT * FROM {name}" for name in MEDSTAR_HOSPITALS
)

sql = f"""
WITH {','.join(cte_parts)}
SELECT * FROM ({union_parts})
WHERE "code|3" IS NOT NULL
"""

raw_medstar = con.sql(sql).pl()
con.close()
print(f"Raw MedStar rows (all codes): {raw_medstar.shape[0]:,}")
print(f"Hospitals loaded: {raw_medstar['hosp_name'].n_unique()}")
```

```{python}
medstar = standardize_columns(raw_medstar)

medstar = medstar.filter(pl.col("cpt_code").is_in(episode_cpt_set))
print(f"Filtered to episode codes: {medstar.shape[0]:,} rows")
print(f"Unique CPT codes found: {medstar['cpt_code'].n_unique()}")
```

## Coverage Summary

```{python}
summary = (
    medstar
    .group_by("hosp_name")
    .agg(
        pl.count().alias("row_count"),
        pl.col("cpt_code").n_unique().alias("unique_codes"),
    )
    .sort("hosp_name")
)
print(summary)
```

```{python}
by_role = (
    medstar
    .join(episode_codes, on="cpt_code", how="left")
    .group_by("clinical_role")
    .agg(
        pl.count().alias("row_count"),
        pl.col("cpt_code").n_unique().alias("unique_codes"),
        pl.col("hosp_name").n_unique().alias("hospitals_reporting"),
    )
    .sort("clinical_role")
)
print(by_role)
```

## Load CMS MPFS National Data

The CMS Physician Fee Schedule provides national benchmark rates.
Download the MPFS national payment file from CMS.gov and place it at
`data/cms/mpfs_national.csv`.

```{python}
cms_path = CMS_DIR / "mpfs_national.csv"

if not cms_path.exists():
    print("=" * 60)
    print("CMS MPFS file not found at:", cms_path)
    print()
    print("To download:")
    print("1. Visit https://www.cms.gov/medicare/payment/fee-schedules/physician/look-up-tool")
    print("2. Download the national payment file (CSV)")
    print("3. Save to:", cms_path)
    print("=" * 60)
    cms_reference = None
else:
    con = get_connection()
    cms_raw = con.sql(f"""
        SELECT *
        FROM read_csv('{cms_path}', all_varchar=true, auto_detect=true)
    """).pl()
    con.close()
    print(f"CMS MPFS raw rows: {cms_raw.shape[0]:,}")
    print(f"Columns: {cms_raw.columns}")
```

```{python}
if cms_path.exists():
    hcpcs_col = [c for c in cms_raw.columns if "hcpcs" in c.lower() or "cpt" in c.lower()][0]

    cms_reference = (
        cms_raw
        .rename({hcpcs_col: "cpt_code"})
        .filter(pl.col("cpt_code").is_in(episode_cpt_set))
    )
    print(f"CMS rows matching episode codes: {cms_reference.shape[0]:,}")
```

## Write Parquet Outputs

```{python}
medstar.write_parquet(INTERMEDIATE_DIR / "medstar_charges.parquet")
print(f"Wrote medstar_charges.parquet: {medstar.shape[0]:,} rows")

if cms_reference is not None:
    cms_reference.write_parquet(INTERMEDIATE_DIR / "cms_reference.parquet")
    print(f"Wrote cms_reference.parquet: {cms_reference.shape[0]:,} rows")
else:
    print("Skipped cms_reference.parquet (CMS file not available)")
```
```

- [ ] **Step 2: Render and verify**

```bash
quarto render 01_ingest.qmd
```

Expected: renders without errors. `data/intermediate/medstar_charges.parquet` is created. CMS parquet may be skipped if the file isn't placed yet.

```bash
python -c "import polars as pl; df = pl.read_parquet('data/intermediate/medstar_charges.parquet'); print(df.shape); print(df.columns)"
```

Expected: columns include `cpt_code`, `charge_gross`, `charge_min`, `charge_max`, `charge_discounted`, `hosp_name`.

- [ ] **Step 3: Commit**

```bash
git add 01_ingest.qmd
git commit -m "add 01_ingest notebook: MedStar and CMS data loading"
```

---

## Task 4: `02_profile.qmd` — Data Profiling & Quality

**Files:**
- Create: `02_profile.qmd`

**Depends on:** Task 3 (`data/intermediate/medstar_charges.parquet` exists)

- [ ] **Step 1: Write `02_profile.qmd`**

```markdown
---
title: "02 — Data Profiling & Quality"
description: |
  Profiles the MedStar charge data: null/zero rates per charge column,
  coverage matrix across hospitals and codes, and anomaly detection.
dependencies:
  - data/intermediate/medstar_charges.parquet
  - data/intermediate/episode_codes.parquet
format: html
jupyter: python3
---

## Load Data

```{python}
import polars as pl
import matplotlib.pyplot as plt
import numpy as np
from _common import INTERMEDIATE_DIR, CHARGE_COLS

medstar = pl.read_parquet(INTERMEDIATE_DIR / "medstar_charges.parquet")
episode_codes = pl.read_parquet(INTERMEDIATE_DIR / "episode_codes.parquet")
print(f"MedStar rows: {medstar.shape[0]:,}")
```

## Charge Column Summary Statistics

For each charge column, we compute null rate, zero rate, and basic
distribution statistics to understand data completeness.

```{python}
total = medstar.shape[0]
stats_rows = []

for col in CHARGE_COLS:
    series = medstar[col]
    null_count = series.null_count()
    numeric = series.drop_nulls().cast(pl.Float64, strict=False).drop_nulls()
    zero_count = (numeric == 0).sum()
    stats_rows.append({
        "column": col,
        "null_rate": round(null_count / total, 3),
        "zero_rate": round(zero_count / total, 3) if len(numeric) > 0 else None,
        "mean": round(numeric.mean(), 2) if len(numeric) > 0 else None,
        "median": round(numeric.median(), 2) if len(numeric) > 0 else None,
        "std": round(numeric.std(), 2) if len(numeric) > 0 else None,
        "min": round(numeric.min(), 2) if len(numeric) > 0 else None,
        "max": round(numeric.max(), 2) if len(numeric) > 0 else None,
    })

stats_df = pl.DataFrame(stats_rows)
print(stats_df)
```

## Coverage Matrix: Hospitals × Clinical Roles

This heatmap shows how many charge rows each hospital reports per clinical
role. Empty cells indicate codes not found in that hospital's data.

```{python}
merged = medstar.join(episode_codes, on="cpt_code", how="left")

coverage = (
    merged
    .group_by(["hosp_name", "clinical_role"])
    .agg(pl.count().alias("n_rows"))
    .pivot(on="clinical_role", index="hosp_name", values="n_rows")
    .fill_null(0)
    .sort("hosp_name")
)

hospitals = coverage["hosp_name"].to_list()
roles = [c for c in coverage.columns if c != "hosp_name"]
matrix = coverage.select(roles).to_numpy()

fig, ax = plt.subplots(figsize=(14, 6))
im = ax.imshow(matrix, aspect="auto", cmap="YlOrRd")
ax.set_xticks(range(len(roles)))
ax.set_xticklabels(roles, rotation=45, ha="right", fontsize=8)
ax.set_yticks(range(len(hospitals)))
ax.set_yticklabels(hospitals, fontsize=8)
plt.colorbar(im, label="Row count")
ax.set_title("Coverage: MedStar Hospitals × Clinical Roles")
plt.tight_layout()
plt.show()
```

## Code-Level Coverage

Which episode codes are present vs. absent across hospitals?

```{python}
codes_in_data = set(medstar["cpt_code"].unique().to_list())
codes_expected = set(episode_codes["cpt_code"].to_list())

found = codes_expected & codes_in_data
missing = codes_expected - codes_in_data

print(f"Episode codes found in data: {len(found)} / {len(codes_expected)}")
if missing:
    missing_roles = (
        episode_codes
        .filter(pl.col("cpt_code").is_in(list(missing)))
        .group_by("clinical_role")
        .agg(pl.col("cpt_code").count().alias("n_missing"))
        .sort("n_missing", descending=True)
    )
    print(f"\nMissing codes by clinical role:")
    print(missing_roles)
```

## Anomaly Detection

Flag rows where charge values are internally inconsistent.

```{python}
anomalies = []

has_min_max = medstar.filter(
    pl.col("charge_min").is_not_null() & pl.col("charge_max").is_not_null()
)
min_gt_max = has_min_max.filter(
    pl.col("charge_min").cast(pl.Float64) > pl.col("charge_max").cast(pl.Float64)
)
anomalies.append({"type": "min > max", "count": min_gt_max.shape[0]})

has_gross_disc = medstar.filter(
    pl.col("charge_gross").is_not_null() & pl.col("charge_discounted").is_not_null()
)
gross_lt_disc = has_gross_disc.filter(
    pl.col("charge_gross").cast(pl.Float64) < pl.col("charge_discounted").cast(pl.Float64)
)
anomalies.append({"type": "gross < discounted", "count": gross_lt_disc.shape[0]})

for col in CHARGE_COLS:
    n_zero = medstar.filter(
        pl.col(col).is_not_null() & (pl.col(col).cast(pl.Float64) == 0)
    ).shape[0]
    anomalies.append({"type": f"zero {col}", "count": n_zero})

anomaly_df = pl.DataFrame(anomalies)
print(anomaly_df)
```

## Assessment

```{python}
print("=" * 60)
print("DATA QUALITY ASSESSMENT")
print("=" * 60)
print()
for row in stats_rows:
    col = row["column"]
    null_pct = row["null_rate"] * 100
    status = "GOOD" if null_pct < 10 else "CAUTION" if null_pct < 50 else "POOR"
    print(f"  {col}: {null_pct:.1f}% null — {status}")
print()
print(f"  Codes found: {len(found)}/{len(codes_expected)}")
print(f"  Codes missing entirely: {len(missing)}")
print()
print("See coverage heatmap above for per-hospital detail.")
```
```

- [ ] **Step 2: Render and verify**

```bash
quarto render 02_profile.qmd
```

Expected: renders with heatmap visualization, anomaly table, and assessment narrative. No Parquet output (analysis-only notebook).

- [ ] **Step 3: Commit**

```bash
git add 02_profile.qmd
git commit -m "add 02_profile notebook: data quality and coverage analysis"
```

---

## Task 5: `03_variance.qmd` — Charge Variance & Reliability

**Files:**
- Create: `03_variance.qmd`

**Depends on:** Task 3 (`data/intermediate/medstar_charges.parquet` exists)

**Produces:** `data/intermediate/code_reliability.parquet` with schema:
- `cpt_code` (Utf8)
- `clinical_role` (Utf8)
- `n_hospitals` (UInt32) — number of hospitals reporting this code
- `cv_gross` (Float64) — coefficient of variation for gross charges
- `cv_discounted` (Float64) — CV for discounted charges
- `iqr_gross` (Float64)
- `iqr_discounted` (Float64)
- `is_reliable` (Boolean) — True if cv < 0.5 and n_hospitals >= 3
- `recommended_charge_type` (Utf8) — whichever of charge_gross/charge_discounted has lower CV

- [ ] **Step 1: Write `03_variance.qmd`**

```markdown
---
title: "03 — Charge Variance & Reliability"
description: |
  Analyzes cross-hospital charge dispersion per CPT code, identifies
  high-variance vs. stable codes, detects outliers, and writes a reliability
  table consumed by 04_episode.
dependencies:
  - data/intermediate/medstar_charges.parquet
  - data/intermediate/episode_codes.parquet
format: html
jupyter: python3
---

## Load Data

```{python}
import polars as pl
import matplotlib.pyplot as plt
import numpy as np
from _common import INTERMEDIATE_DIR, CHARGE_COLS

medstar = pl.read_parquet(INTERMEDIATE_DIR / "medstar_charges.parquet")
episode_codes = pl.read_parquet(INTERMEDIATE_DIR / "episode_codes.parquet")

medstar_f = medstar.with_columns([
    pl.col(c).cast(pl.Float64, strict=False) for c in CHARGE_COLS
])
print(f"Rows: {medstar_f.shape[0]:,}, Unique codes: {medstar_f['cpt_code'].n_unique()}")
```

## Cross-Hospital Charge Dispersion

For each CPT code, we compute the coefficient of variation (CV = std/mean),
IQR, and range across hospitals. Lower CV indicates more consistent pricing.

```{python}
def compute_cv(series: pl.Series) -> float | None:
    s = series.drop_nulls()
    if len(s) < 2:
        return None
    mean = s.mean()
    if mean == 0:
        return None
    return s.std() / mean

code_stats = []

for code in medstar_f["cpt_code"].unique().sort().to_list():
    subset = medstar_f.filter(pl.col("cpt_code") == code)
    n_hosp = subset["hosp_name"].n_unique()

    gross = subset["charge_gross"].drop_nulls()
    disc = subset["charge_discounted"].drop_nulls()

    cv_g = compute_cv(subset["charge_gross"])
    cv_d = compute_cv(subset["charge_discounted"])

    iqr_g = float(gross.quantile(0.75) - gross.quantile(0.25)) if len(gross) >= 4 else None
    iqr_d = float(disc.quantile(0.75) - disc.quantile(0.25)) if len(disc) >= 4 else None

    code_stats.append({
        "cpt_code": code,
        "n_hospitals": n_hosp,
        "cv_gross": round(cv_g, 3) if cv_g is not None else None,
        "cv_discounted": round(cv_d, 3) if cv_d is not None else None,
        "iqr_gross": round(iqr_g, 2) if iqr_g is not None else None,
        "iqr_discounted": round(iqr_d, 2) if iqr_d is not None else None,
    })

variance_df = pl.DataFrame(code_stats)
print(f"Codes analyzed: {variance_df.shape[0]}")
print(variance_df.sort("cv_gross", descending=True).head(10))
```

## High-Variance vs. Stable Codes

```{python}
has_cv = variance_df.filter(pl.col("cv_gross").is_not_null())
if has_cv.shape[0] > 0:
    fig, ax = plt.subplots(figsize=(12, 5))
    sorted_df = has_cv.sort("cv_gross", descending=True)
    codes = sorted_df["cpt_code"].to_list()
    cvs = sorted_df["cv_gross"].to_list()

    colors = ["#d32f2f" if cv > 0.5 else "#388e3c" for cv in cvs]
    ax.barh(range(len(codes)), cvs, color=colors)
    ax.set_yticks(range(len(codes)))
    ax.set_yticklabels(codes, fontsize=7)
    ax.axvline(x=0.5, color="black", linestyle="--", linewidth=0.8, label="CV = 0.5 threshold")
    ax.set_xlabel("Coefficient of Variation (Gross Charges)")
    ax.set_title("Cross-Hospital Charge Variance by CPT Code")
    ax.legend()
    plt.tight_layout()
    plt.show()
```

## Within-Hospital Consistency

Do the same codes show consistent pricing across billing classes and
settings within a single hospital?

```{python}
within_hosp = (
    medstar_f
    .group_by(["hosp_name", "cpt_code"])
    .agg([
        pl.col("charge_gross").std().alias("within_std"),
        pl.col("charge_gross").mean().alias("within_mean"),
        pl.count().alias("n_rows"),
    ])
    .filter(pl.col("n_rows") > 1)
    .with_columns(
        (pl.col("within_std") / pl.col("within_mean")).alias("within_cv")
    )
    .filter(pl.col("within_cv").is_not_null())
)

high_within_var = within_hosp.filter(pl.col("within_cv") > 0.3).sort("within_cv", descending=True)
print(f"Code-hospital pairs with within-hospital CV > 0.3: {high_within_var.shape[0]}")
if high_within_var.shape[0] > 0:
    print(high_within_var.head(10))
```

## Outlier Detection

Hospitals with charges >2 standard deviations from the per-code mean.

```{python}
code_means = (
    medstar_f
    .group_by("cpt_code")
    .agg([
        pl.col("charge_gross").mean().alias("mean_gross"),
        pl.col("charge_gross").std().alias("std_gross"),
    ])
    .filter(pl.col("std_gross").is_not_null() & (pl.col("std_gross") > 0))
)

with_stats = medstar_f.join(code_means, on="cpt_code", how="inner")

outliers = with_stats.filter(
    ((pl.col("charge_gross") - pl.col("mean_gross")).abs() / pl.col("std_gross")) > 2
)

print(f"Outlier rows (>2 SD from mean): {outliers.shape[0]}")
if outliers.shape[0] > 0:
    outlier_summary = (
        outliers
        .group_by("hosp_name")
        .agg(pl.count().alias("n_outliers"))
        .sort("n_outliers", descending=True)
    )
    print(outlier_summary)
```

## Reliability Classification

A code is classified as **reliable** if:
- CV (gross) < 0.5 *and*
- Reported by at least 3 hospitals

The recommended charge type is whichever of gross/discounted has the lower CV.

```{python}
reliability = (
    variance_df
    .join(episode_codes, on="cpt_code", how="left")
    .with_columns([
        (
            (pl.col("cv_gross").is_not_null()) &
            (pl.col("cv_gross") < 0.5) &
            (pl.col("n_hospitals") >= 3)
        ).alias("is_reliable"),
        pl.when(
            pl.col("cv_discounted").is_not_null() &
            pl.col("cv_gross").is_not_null() &
            (pl.col("cv_discounted") < pl.col("cv_gross"))
        )
        .then(pl.lit("charge_discounted"))
        .otherwise(pl.lit("charge_gross"))
        .alias("recommended_charge_type"),
    ])
    .select([
        "cpt_code", "clinical_role", "n_hospitals",
        "cv_gross", "cv_discounted",
        "iqr_gross", "iqr_discounted",
        "is_reliable", "recommended_charge_type",
    ])
)

n_reliable = reliability.filter(pl.col("is_reliable")).shape[0]
print(f"Reliable codes: {n_reliable} / {reliability.shape[0]}")
print()
print(reliability.sort("is_reliable", descending=True))
```

## Write Reliability Table

```{python}
out_path = INTERMEDIATE_DIR / "code_reliability.parquet"
reliability.write_parquet(out_path)
print(f"Wrote {reliability.shape[0]} rows to {out_path}")
```
```

- [ ] **Step 2: Render and verify**

```bash
quarto render 03_variance.qmd
```

Expected: renders with CV bar chart, within-hospital analysis, outlier table, and reliability classification. Verify `data/intermediate/code_reliability.parquet`:

```bash
python -c "import polars as pl; df = pl.read_parquet('data/intermediate/code_reliability.parquet'); print(df.columns); print(df.shape)"
```

Expected: columns are `cpt_code`, `clinical_role`, `n_hospitals`, `cv_gross`, `cv_discounted`, `iqr_gross`, `iqr_discounted`, `is_reliable`, `recommended_charge_type`.

- [ ] **Step 3: Commit**

```bash
git add 03_variance.qmd
git commit -m "add 03_variance notebook: charge dispersion and reliability analysis"
```

---

## Task 6: `04_episode.qmd` — Episode Cost Assembly

**Files:**
- Create: `04_episode.qmd`

**Depends on:** Task 3 (`medstar_charges.parquet`), Task 5 (`code_reliability.parquet`)

- [ ] **Step 1: Write `04_episode.qmd`**

```markdown
---
title: "04 — Episode Cost Assembly"
description: |
  Assembles the full liver biopsy episode cost per hospital using the
  reliability-filtered charge data, with breakdown by clinical role and
  sensitivity analysis across charge types.
dependencies:
  - data/intermediate/medstar_charges.parquet
  - data/intermediate/code_reliability.parquet
  - data/intermediate/episode_codes.parquet
format: html
jupyter: python3
---

## Load Data

```{python}
import polars as pl
import matplotlib.pyplot as plt
from _common import INTERMEDIATE_DIR, CHARGE_COLS, EPISODE_FREQUENCIES

medstar = pl.read_parquet(INTERMEDIATE_DIR / "medstar_charges.parquet")
reliability = pl.read_parquet(INTERMEDIATE_DIR / "code_reliability.parquet")
episode_codes = pl.read_parquet(INTERMEDIATE_DIR / "episode_codes.parquet")

medstar_f = medstar.with_columns([
    pl.col(c).cast(pl.Float64, strict=False) for c in CHARGE_COLS
])
print(f"Charges: {medstar_f.shape[0]:,} rows")
print(f"Reliable codes: {reliability.filter(pl.col('is_reliable')).shape[0]}")
```

## Episode Bundle Definition

The episode assumes these services at the specified frequencies.
Adjust quantities to reflect the typical care pathway.

```{python}
freq_df = pl.DataFrame([
    {"key": k, "cpt_code": str(v["code"]), "qty": v["qty"]}
    for k, v in EPISODE_FREQUENCIES.items()
])
print(freq_df)
```

## Compute Per-Hospital Episode Cost

For each hospital, we take the median charge per code (across billing
classes/settings), multiply by the episode frequency, and sum. We use the
recommended charge type from the reliability analysis where available.

```{python}
reliable_codes = reliability.filter(pl.col("is_reliable"))
episode_bundle = freq_df.join(
    reliable_codes.select(["cpt_code", "recommended_charge_type"]),
    on="cpt_code",
    how="left",
).with_columns(
    pl.col("recommended_charge_type").fill_null("charge_gross")
)
print(f"Episode bundle codes: {episode_bundle.shape[0]}")
print(episode_bundle)
```

```{python}
episode_costs = []

for hosp in medstar_f["hosp_name"].unique().sort().to_list():
    hosp_data = medstar_f.filter(pl.col("hosp_name") == hosp)
    total = 0.0
    components = []

    for row in episode_bundle.iter_rows(named=True):
        code = row["cpt_code"]
        qty = row["qty"]
        charge_col = row["recommended_charge_type"]

        code_data = hosp_data.filter(pl.col("cpt_code") == code)
        if code_data.shape[0] == 0:
            components.append({"code": code, "key": row["key"], "charge": None, "qty": qty})
            continue

        median_charge = code_data[charge_col].drop_nulls().median()
        if median_charge is None:
            median_charge = code_data["charge_gross"].drop_nulls().median()

        cost = (median_charge or 0) * qty
        total += cost
        components.append({"code": code, "key": row["key"], "charge": median_charge, "qty": qty})

    episode_costs.append({
        "hosp_name": hosp,
        "episode_total": round(total, 2),
        **{c["key"]: round(c["charge"] * c["qty"], 2) if c["charge"] else None for c in components},
    })

episode_df = pl.DataFrame(episode_costs)
print(episode_df.sort("episode_total", descending=True))
```

## Episode Cost Breakdown by Clinical Role

```{python}
role_map = dict(zip(
    episode_codes["cpt_code"].to_list(),
    episode_codes["clinical_role"].to_list()
))

role_costs = []
for row in episode_bundle.iter_rows(named=True):
    code = row["cpt_code"]
    charge_col = row["recommended_charge_type"]
    code_data = medstar_f.filter(pl.col("cpt_code") == code)
    median = code_data[charge_col].drop_nulls().median() if code_data.shape[0] > 0 else None
    role_costs.append({
        "key": row["key"],
        "cpt_code": code,
        "clinical_role": role_map.get(code, "unknown"),
        "median_charge": median,
        "qty": row["qty"],
        "line_total": round(median * row["qty"], 2) if median else None,
    })

role_df = pl.DataFrame(role_costs).filter(pl.col("line_total").is_not_null())
print(role_df)
```

```{python}
if role_df.shape[0] > 0:
    by_role = role_df.group_by("clinical_role").agg(pl.col("line_total").sum())
    labels = by_role["clinical_role"].to_list()
    values = by_role["line_total"].to_list()

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(labels, values, color="#1976d2")
    ax.set_xlabel("Cost ($)")
    ax.set_title("Episode Cost Breakdown by Clinical Role")
    plt.tight_layout()
    plt.show()
```

## Sensitivity Analysis: Gross vs. Discounted Charges

How does the episode cost change when using gross charges vs. discounted
cash charges across all codes?

```{python}
sensitivity = []

for charge_type in ["charge_gross", "charge_discounted"]:
    for hosp in medstar_f["hosp_name"].unique().sort().to_list():
        hosp_data = medstar_f.filter(pl.col("hosp_name") == hosp)
        total = 0.0
        for row in freq_df.iter_rows(named=True):
            code = row["cpt_code"]
            code_data = hosp_data.filter(pl.col("cpt_code") == code)
            median = code_data[charge_type].drop_nulls().median() if code_data.shape[0] > 0 else None
            total += (median or 0) * row["qty"]
        sensitivity.append({
            "hosp_name": hosp,
            "charge_type": charge_type,
            "episode_total": round(total, 2),
        })

sens_df = pl.DataFrame(sensitivity)
sens_pivot = sens_df.pivot(on="charge_type", index="hosp_name", values="episode_total")
print(sens_pivot.sort("charge_gross", descending=True))
```

```{python}
if sens_df.shape[0] > 0:
    hospitals = sorted(medstar_f["hosp_name"].unique().to_list())
    gross_vals = [
        sens_df.filter((pl.col("hosp_name") == h) & (pl.col("charge_type") == "charge_gross"))["episode_total"][0]
        for h in hospitals
    ]
    disc_vals = [
        sens_df.filter((pl.col("hosp_name") == h) & (pl.col("charge_type") == "charge_discounted"))["episode_total"][0]
        for h in hospitals
    ]

    x = range(len(hospitals))
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar([i - 0.2 for i in x], gross_vals, 0.4, label="Gross", color="#1976d2")
    ax.bar([i + 0.2 for i in x], disc_vals, 0.4, label="Discounted", color="#388e3c")
    ax.set_xticks(list(x))
    ax.set_xticklabels(hospitals, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Episode Total ($)")
    ax.set_title("Episode Cost: Gross vs. Discounted Charges")
    ax.legend()
    plt.tight_layout()
    plt.show()
```

## Write Episode Costs

```{python}
episode_df.write_parquet(INTERMEDIATE_DIR / "episode_costs.parquet")
print(f"Wrote episode_costs.parquet: {episode_df.shape[0]} rows")
```
```

- [ ] **Step 2: Render and verify**

```bash
quarto render 04_episode.qmd
```

Expected: renders with episode cost table, role breakdown bar chart, and sensitivity comparison. Verify `data/intermediate/episode_costs.parquet`:

```bash
python -c "import polars as pl; df = pl.read_parquet('data/intermediate/episode_costs.parquet'); print(df.columns); print(df)"
```

Expected: one row per hospital with `hosp_name`, `episode_total`, and per-component columns.

- [ ] **Step 3: Commit**

```bash
git add 04_episode.qmd
git commit -m "add 04_episode notebook: episode cost assembly and sensitivity analysis"
```

---

## Task 7: `05_benchmark.qmd` — National Benchmarking

**Files:**
- Create: `05_benchmark.qmd`

**Depends on:** Task 3 (`medstar_charges.parquet`, `cms_reference.parquet`), Task 6 (`episode_costs.parquet`)

- [ ] **Step 1: Write `05_benchmark.qmd`**

```markdown
---
title: "05 — National Benchmarking"
description: |
  Compares MedStar per-code charges and episode costs against CMS MPFS
  national rates. Computes charge-to-allowed ratios and visualizes where
  MedStar sits relative to national benchmarks.
dependencies:
  - data/intermediate/medstar_charges.parquet
  - data/intermediate/cms_reference.parquet
  - data/intermediate/episode_costs.parquet
format: html
jupyter: python3
---

## Load Data

```{python}
import polars as pl
import matplotlib.pyplot as plt
import numpy as np
from _common import INTERMEDIATE_DIR, CHARGE_COLS, EPISODE_FREQUENCIES

medstar = pl.read_parquet(INTERMEDIATE_DIR / "medstar_charges.parquet")
episode_costs = pl.read_parquet(INTERMEDIATE_DIR / "episode_costs.parquet")

medstar_f = medstar.with_columns([
    pl.col(c).cast(pl.Float64, strict=False) for c in CHARGE_COLS
])

cms_path = INTERMEDIATE_DIR / "cms_reference.parquet"
if not cms_path.exists():
    print("WARNING: cms_reference.parquet not found.")
    print("Run 01_ingest.qmd with CMS MPFS data to enable benchmarking.")
    cms = None
else:
    cms = pl.read_parquet(cms_path)
    print(f"CMS reference rows: {cms.shape[0]:,}")
    print(f"CMS columns: {cms.columns}")
```

## Identify CMS Price Columns

CMS MPFS files vary in column naming. We detect the facility and
non-facility price columns dynamically.

```{python}
if cms is not None:
    price_candidates = {
        "facility": ["fac_price", "facility_price", "par_fee_fac", "fee_fac"],
        "non_facility": ["non_fac_price", "nonfacility_price", "par_fee_nonfac", "fee_nonfac"],
    }

    cms_cols_lower = {c.lower(): c for c in cms.columns}
    fac_col = None
    nonfac_col = None

    for candidate in price_candidates["facility"]:
        if candidate in cms_cols_lower:
            fac_col = cms_cols_lower[candidate]
            break
    for candidate in price_candidates["non_facility"]:
        if candidate in cms_cols_lower:
            nonfac_col = cms_cols_lower[candidate]
            break

    if fac_col:
        print(f"CMS facility price column: {fac_col}")
    if nonfac_col:
        print(f"CMS non-facility price column: {nonfac_col}")
    if not fac_col and not nonfac_col:
        print("WARNING: Could not identify CMS price columns.")
        print(f"Available columns: {cms.columns}")
```

## Per-Code Comparison: MedStar vs. CMS

```{python}
if cms is not None and fac_col is not None:
    medstar_medians = (
        medstar_f
        .group_by("cpt_code")
        .agg(pl.col("charge_gross").median().alias("medstar_median_gross"))
    )

    cms_prices = (
        cms
        .select(["cpt_code", fac_col])
        .rename({fac_col: "cms_fac_price"})
        .with_columns(pl.col("cms_fac_price").cast(pl.Float64, strict=False))
        .filter(pl.col("cms_fac_price").is_not_null() & (pl.col("cms_fac_price") > 0))
    )

    comparison = medstar_medians.join(cms_prices, on="cpt_code", how="inner")
    comparison = comparison.with_columns(
        (pl.col("medstar_median_gross") / pl.col("cms_fac_price")).round(2).alias("charge_to_allowed_ratio")
    )

    print(f"Codes with both MedStar and CMS data: {comparison.shape[0]}")
    print(comparison.sort("charge_to_allowed_ratio", descending=True))
else:
    print("Skipping per-code comparison (CMS data not available)")
    comparison = None
```

## Charge-to-Allowed Ratios by Hospital

```{python}
if cms is not None and fac_col is not None:
    hosp_ratios = []
    for hosp in medstar_f["hosp_name"].unique().sort().to_list():
        hosp_data = medstar_f.filter(pl.col("hosp_name") == hosp)
        hosp_medians = (
            hosp_data
            .group_by("cpt_code")
            .agg(pl.col("charge_gross").median().alias("medstar_gross"))
        )
        merged = hosp_medians.join(cms_prices, on="cpt_code", how="inner")
        if merged.shape[0] > 0:
            ratios = (merged["medstar_gross"] / merged["cms_fac_price"]).drop_nulls()
            hosp_ratios.append({
                "hosp_name": hosp,
                "median_ratio": round(ratios.median(), 2) if len(ratios) > 0 else None,
                "mean_ratio": round(ratios.mean(), 2) if len(ratios) > 0 else None,
                "n_codes": merged.shape[0],
            })

    ratio_df = pl.DataFrame(hosp_ratios)
    print(ratio_df.sort("median_ratio", descending=True))

    fig, ax = plt.subplots(figsize=(10, 5))
    hospitals = ratio_df["hosp_name"].to_list()
    ratios = ratio_df["median_ratio"].to_list()
    colors = ["#d32f2f" if r and r > 3 else "#1976d2" for r in ratios]
    ax.barh(hospitals, ratios, color=colors)
    ax.axvline(x=1.0, color="black", linestyle="--", linewidth=0.8, label="CMS parity")
    ax.set_xlabel("Median Charge-to-Allowed Ratio")
    ax.set_title("MedStar Hospitals: Charge-to-CMS Ratios")
    ax.legend()
    plt.tight_layout()
    plt.show()
else:
    print("Skipping hospital ratio analysis (CMS data not available)")
```

## Episode-Level Comparison

```{python}
if cms is not None and fac_col is not None:
    cms_episode_total = 0.0
    cms_components = []
    for key, spec in EPISODE_FREQUENCIES.items():
        code = str(spec["code"])
        qty = spec["qty"]
        cms_row = cms_prices.filter(pl.col("cpt_code") == code)
        price = cms_row["cms_fac_price"][0] if cms_row.shape[0] > 0 else None
        cost = (price or 0) * qty
        cms_episode_total += cost
        cms_components.append({"key": key, "cpt_code": code, "cms_price": price, "qty": qty, "line_total": round(cost, 2)})

    print(f"CMS episode total (facility): ${cms_episode_total:,.2f}")
    print()
    cms_comp_df = pl.DataFrame(cms_components)
    print(cms_comp_df)

    print()
    print("MedStar episode totals for comparison:")
    for row in episode_costs.sort("episode_total").iter_rows(named=True):
        pct = ((row["episode_total"] / cms_episode_total) - 1) * 100 if cms_episode_total > 0 else None
        pct_str = f"{pct:+.1f}%" if pct is not None else "N/A"
        print(f"  {row['hosp_name']}: ${row['episode_total']:,.2f} ({pct_str} vs CMS)")
else:
    print("Skipping episode comparison (CMS data not available)")
```

## Visualization: MedStar Distribution vs. CMS Benchmark

```{python}
if cms is not None and fac_col is not None and cms_episode_total > 0:
    totals = episode_costs["episode_total"].to_list()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(
        episode_costs["hosp_name"].to_list(),
        totals,
        color="#1976d2",
        label="MedStar",
    )
    ax.axvline(x=cms_episode_total, color="#d32f2f", linewidth=2, linestyle="--", label=f"CMS National (${cms_episode_total:,.0f})")
    ax.set_xlabel("Episode Total ($)")
    ax.set_title("Liver Biopsy Episode Cost: MedStar Hospitals vs. CMS National")
    ax.legend()
    plt.tight_layout()
    plt.show()
else:
    print("Skipping visualization (CMS data not available)")
```

## Summary & Limitations

```{python}
print("=" * 60)
print("FINDINGS SUMMARY")
print("=" * 60)
print()

totals = episode_costs["episode_total"].to_list()
print(f"MedStar episode cost range: ${min(totals):,.2f} – ${max(totals):,.2f}")
print(f"MedStar median episode cost: ${sorted(totals)[len(totals)//2]:,.2f}")

if cms is not None and fac_col is not None and cms_episode_total > 0:
    print(f"CMS national episode cost:   ${cms_episode_total:,.2f}")
    median_total = sorted(totals)[len(totals) // 2]
    print(f"MedStar median vs CMS:       {((median_total / cms_episode_total) - 1) * 100:+.1f}%")

print()
print("LIMITATIONS:")
print("  - MedStar charges are list prices, not negotiated rates")
print("  - CMS MPFS reflects Medicare allowed amounts, not commercial rates")
print("  - Episode frequencies are assumed (adjustable in _common.py)")
print("  - Some episode codes may not be reported by all hospitals")
print("  - Reliability filtering excludes high-variance codes from the primary estimate")
```
```

- [ ] **Step 2: Render and verify**

```bash
quarto render 05_benchmark.qmd
```

Expected: renders with all sections. CMS comparison sections show results if `cms_reference.parquet` exists, or informative skip messages if not. MedStar-only analysis (episode cost range) always works.

- [ ] **Step 3: Commit**

```bash
git add 05_benchmark.qmd
git commit -m "add 05_benchmark notebook: CMS national benchmarking"
```

---

## Task 8: Final Integration — .gitignore and Render Check

**Files:**
- Create/Modify: `.gitignore`

- [ ] **Step 1: Add `.gitignore` entries for generated files**

```
data/intermediate/*.parquet
data/cms/
*.html
*_files/
.quarto/
__pycache__/
```

- [ ] **Step 2: Run full pipeline end-to-end**

```bash
quarto render 00_setup.qmd && \
quarto render 01_ingest.qmd && \
quarto render 02_profile.qmd && \
quarto render 03_variance.qmd && \
quarto render 04_episode.qmd && \
quarto render 05_benchmark.qmd
```

Expected: all six notebooks render without errors. Parquet files exist in `data/intermediate/`.

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "add gitignore for generated parquet, html, and cache files"
```
