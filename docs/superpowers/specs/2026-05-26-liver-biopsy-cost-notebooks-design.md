# Liver Biopsy Episode Cost Analysis -- Notebook Series Design

## Goal

Create a series of Quarto (.qmd) notebooks that assess the usefulness of hospital price transparency data for modeling the standard cost of care for a liver biopsy testing for transplanted organ rejection.

## Context

- **Audience**: Internal team reference (enough narrative to onboard a new member)
- **Clinical scope**: Full episode cost -- consult, imaging, biopsy procedure (CPT 47000), pathology, infusion, follow-up
- **Data sources**: MedStar Health 10-hospital price transparency CSVs (2025) + CMS Physician Fee Schedule (MPFS) for national benchmarks
- **Data quality focus**: Charge variance and reliability across hospitals, not just completeness
- **Stack**: Python 3.12+, DuckDB (query engine), Polars (dataframes), Quarto (rendering)

## Episode CPT Code Bundle

### Inpatient codes
E/M and related services: 99498, 99496, 99495, 99494, 99493, 99492, 99491, 99490, 99484, 99483, 99480, 99465, 99464, 99463, 99461, 99443, 99442, 99441, 99439, 99429, 99417, 99407, 99406, 99399, 99397, 99396, 99395, 99394, 99387, 99386, 99385, 99384, 99368, 99367, 99366, 99358, 99345, 99291, 99285, 99284, 99283, 99282, 99281, 99223, 99222, 99221, 99215, 99214, 99213, 99212, 99211, 99205, 99204, 99203, 99202

Infusion codes: 96368, 96367, 96366, 96365, 96361, 96360

Procedure codes: 64530 (nerve block), 12031 (wound repair)

### Outpatient codes
96360, 96361, 96365, 96366, 96367, 96368, 12031, 64530

### Biopsy
47000

## Architecture

### Organization: Linear Pipeline (Approach A)

Six numbered notebooks in the project root, each producing Parquet intermediates consumed by downstream notebooks.

### Shared code

`_common.py` module containing:
- CPT code lists with clinical role tags (inpatient/outpatient episode bundles)
- DuckDB connection factory
- MedStar hospital URL registry
- Column name standardization mapping

### Intermediate data flow

```
00_setup.qmd  -->  data/intermediate/episode_codes.parquet
01_ingest.qmd -->  data/intermediate/medstar_charges.parquet
                   data/intermediate/cms_reference.parquet
02_profile.qmd --> (analysis only, no output)
03_variance.qmd -> data/intermediate/code_reliability.parquet
04_episode.qmd --> data/intermediate/episode_costs.parquet
05_benchmark.qmd > (analysis only, final findings)
```

### Convention

Each notebook starts with:
1. YAML header with title, description, and listed dependencies
2. First code cell importing from `_common.py` and loading required Parquet inputs

## Notebook Designs

### 00_setup.qmd -- Environment & Code Definitions

- Validate Python environment (polars, duckdb versions)
- Define the full CPT episode bundle with clinical role tags per code (E/M consult, infusion administration, nerve block, biopsy procedure, etc.)
- Tag each code with setting: inpatient, outpatient, or both
- Write `episode_codes.parquet`: columns `cpt_code`, `description`, `clinical_role`, `setting`
- Smoke-test DuckDB connection

### 01_ingest.qmd -- Data Ingestion

- Load all 10 MedStar hospital CSVs via DuckDB `read_csv` from URLs (existing `hosp_costs.sql` pattern)
- Filter to episode-relevant CPT codes (inner join against episode_codes)
- Standardize column names: `code|3` -> `cpt_code`, `standard_charge|gross` -> `charge_gross`, etc.
- Source CMS MPFS data for the same CPT codes as national reference
- Write `medstar_charges.parquet` and `cms_reference.parquet`
- Summary table: row counts per hospital, per code category

### 02_profile.qmd -- Data Profiling & Quality

- Per charge column (gross, min, max, discounted_cash): null rate, zero rate, distribution stats
- Coverage matrix: which hospitals report which codes (heatmap visualization)
- Flag anomalies: codes where min > max, gross < discounted, zero charges
- Narrative assessment: what can and cannot be reliably modeled given these profiles

### 03_variance.qmd -- Charge Variance & Reliability

- Cross-hospital dispersion per CPT code: coefficient of variation, IQR, range
- Identify high-variance vs. stable codes
- Within-hospital consistency: same codes across billing classes/settings
- Outlier detection: hospitals with charges >2 SD from mean per code
- Reliability conclusion: which codes/charge types are trustworthy for episode costing
- Write `code_reliability.parquet`: per-code flags (reliable/unreliable) with CV and recommended charge type, consumed by 04_episode

### 04_episode.qmd -- Episode Cost Assembly

- Define episode bundle: which codes at what frequency (1 biopsy, 1 consult, N infusions, etc.)
- Compute per-hospital episode cost using reliable charge types from 03_variance
- Episode cost breakdown by clinical role (procedure vs. pathology vs. E/M share)
- Sensitivity analysis: episode cost under gross vs. discounted charges
- Write `episode_costs.parquet`

### 05_benchmark.qmd -- National Benchmarking

- Compare MedStar per-code charges against CMS MPFS rates
- Compute charge-to-allowed ratios per hospital
- Episode-level comparison: MedStar vs. CMS-derived episode cost
- Visualization: where MedStar sits in the national distribution
- Summary findings and limitations

## File Structure (after implementation)

```
diagnostic_costs/
├── _common.py
├── 00_setup.qmd
├── 01_ingest.qmd
├── 02_profile.qmd
├── 03_variance.qmd
├── 04_episode.qmd
├── 05_benchmark.qmd
├── pyproject.toml
├── queries/
│   ├── hosp_costs.sql
│   ├── liver_biopsy_cost.sql
│   └── diagnostic_cost.sql
├── data/
│   ├── intermediate/
│   │   ├── episode_codes.parquet
│   │   ├── medstar_charges.parquet
│   │   ├── cms_reference.parquet
│   │   ├── code_reliability.parquet
│   │   └── episode_costs.parquet
│   └── medstar/
│       └── sources.txt
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-05-26-liver-biopsy-cost-notebooks-design.md
```
