# Diagnostic Costs — Liver Biopsy Episode Pricing

Models the standard cost of a liver biopsy episode (transplanted organ
rejection monitoring) using MedStar Health price-transparency data, then
quantifies the per-patient savings of replacing biopsy with Epigenetic
Compass, a non-invasive epigenetic diagnostic.

## Results

A liver biopsy episode runs **$3,000–$10,000+** depending on clinical
setting and patient complexity. Epigenetic Compass replaces that episode
with a **$2,000 blood draw** — no sedation, no imaging, no
post-procedure observation. A 10,000-patient Monte Carlo simulation
confirms the savings across both inpatient and outpatient protocols;
see the [full summary](notebooks/05_simulation.qmd#investment-thesis).

The analysis behind that claim:

1. **Source data.** Price-transparency filings from
   [9 MedStar hospitals](notebooks/01_ingest.qmd#load-medstar-hospital-data)
   covering [21 CPT codes across 6 clinical roles](notebooks/01_ingest.qmd#coverage-summary) —
   published charges, not estimates.

2. **Quality controls.** Validated
   [charge completeness](notebooks/02_profile.qmd#charge-column-completeness),
   [code coverage](notebooks/02_profile.qmd#code-coverage), and
   [structural consistency](notebooks/02_profile.qmd#structural-anomalies)
   before downstream use
   ([verdict](notebooks/02_profile.qmd#verdict)).

3. **Pricing stability.** Cross-hospital
   [charge variance](notebooks/03_variance.qmd#cross-hospital-charge-dispersion)
   is low for most episode codes; each code's
   [reliability classification](notebooks/03_variance.qmd#reliability-classification)
   determined which pricing signals entered the episode model.

4. **Episode assembly.** Built a
   [7-component episode cost](notebooks/04_episode.qmd#episode-cost-buildup)
   from the reliable codes, compared
   [across hospitals](notebooks/04_episode.qmd#per-hospital-comparison),
   and tested sensitivity to
   [gross vs. discounted charge types](notebooks/04_episode.qmd#sensitivity-gross-vs.-discounted-charges).

5. **Cost comparison.** A
   [Monte Carlo simulation](notebooks/05_simulation.qmd#simulated-biopsy-episode-costs)
   across 10,000 patients shows Epigenetic Compass
   [reduces costs in both settings](notebooks/05_simulation.qmd#cost-savings-distribution)
   and across the full complexity spectrum. For market context: existing
   kidney-transplant cfDNA tests (AlloSure, Prospera) are reimbursed at
   ~$2,850 — Epigenetic Compass
   [prices $850 below that precedent](notebooks/05_simulation.qmd#head-to-head-comparison)
   in a segment with no current non-invasive alternative.

## Methods

### Data Pipeline

| Notebook | Purpose |
|----------|---------|
| [`00_setup`](notebooks/00_setup.qmd) | Environment validation, [episode CPT code reference](notebooks/00_setup.qmd#episode-cpt-code-bundle), DuckDB database test |
| [`01_ingest`](notebooks/01_ingest.qmd) | Loads [9 MedStar CSVs](notebooks/01_ingest.qmd#load-medstar-hospital-data) via DuckDB, filters to episode codes, writes `medstar_charges.parquet` |
| [`02_profile`](notebooks/02_profile.qmd) | Data quality: [completeness](notebooks/02_profile.qmd#charge-column-completeness), [code coverage](notebooks/02_profile.qmd#code-coverage), [structural anomalies](notebooks/02_profile.qmd#structural-anomalies) |
| [`03_variance`](notebooks/03_variance.qmd) | [Cross-hospital charge dispersion](notebooks/03_variance.qmd#cross-hospital-charge-dispersion), [reliability classification](notebooks/03_variance.qmd#reliability-classification) per code |
| [`04_episode`](notebooks/04_episode.qmd) | [Episode cost assembly](notebooks/04_episode.qmd#episode-cost-buildup), [per-hospital comparison](notebooks/04_episode.qmd#per-hospital-comparison), [sensitivity analysis](notebooks/04_episode.qmd#sensitivity-gross-vs.-discounted-charges) |
| [`05_simulation`](notebooks/05_simulation.qmd) | [Monte Carlo cost comparison](notebooks/05_simulation.qmd#simulated-biopsy-episode-costs): biopsy vs. [alternative diagnostics](notebooks/05_simulation.qmd#the-diagnostic-landscape) |

Notebooks run in order. Each writes intermediate parquet files to `data/intermediate/` consumed by downstream notebooks.[^coverage]

[^coverage]: The episode cost spread across hospitals ($805–$9,937) reflects scope of services, not price variation. Under CMS rules, hospitals only publish charges for procedures they perform — most MedStar community hospitals don't offer liver biopsies or nerve blocks, so only [3 of 9 hospitals](notebooks/04_episode.qmd#per-hospital-component-coverage) produce a meaningful full-episode total.

### Shared Module

`_common.py` contains hospital URLs, column mappings, CPT code groups (6 clinical roles, 21 codes), episode frequency definitions, and utility functions shared across all notebooks.

### Setup

```bash
uv sync
uv run quarto render
```

Rendered output goes to `_output/` (gitignored).

### Tests

```bash
uv run pytest
```
