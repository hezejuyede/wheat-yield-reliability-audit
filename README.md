# Wheat-Yield Reliability Audit

Public data and reproducibility materials for the manuscript **“Reliability Auditing and Capacity-Constrained Review for Wheat-Yield Decision Support under Temporal and Spatial Shift”**.

This repository contains the public raw data used in the study, processed leakage-safe panels and frozen splits, deterministic analysis code, tests, case-level predictions, exact-inference outputs, interval and review audits, and figure data.

## Data sources

- National Statistical Committee of the Kyrgyz Republic: *Crops yield by territory* (version 1.1), annual wheat yield by oblast, 1991–2025.
- Our World in Data annual temperature anomalies derived from modified Copernicus ERA5 information.

## Reproducibility

Run:

```bash
python 04_CODE/run_all.py
```

The workflow regenerates the reported outputs and executes the automated tests included in `04_CODE/tests/`.

## Manuscript data-availability statement

The datasets and reproducibility materials supporting the study are publicly available in this repository.
