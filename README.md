# Wheat-Yield Reliability Audit

Public data release for the manuscript **“Reliability Auditing and Capacity-Constrained Review for Wheat-Yield Decision Support under Temporal and Spatial Shift”**.

## Public extracted datasets

The repository currently publishes the two analysis-ready source series used by the study:

- `03_DATA/processed/kyrgyz_wheat_yield_1991_2025.csv` — seven Kyrgyz oblasts × 35 years (245 observations), annual wheat yield in centners per hectare.
- `03_DATA/processed/kyrgyz_temperature_anomaly_1991_2025.csv` — Kyrgyzstan annual temperature anomaly, 1991–2025, relative to 1991–2020.

Supporting provenance, variable definitions, licensing notes and the data audit are also included under `03_DATA/`.

## Data sources

- National Statistical Committee of the Kyrgyz Republic: *Crops' yield by territory* (version 1.1), annual wheat yield by oblast, 1991–2025.
- Our World in Data annual temperature anomalies, adapted from modified Copernicus Climate Change Service ERA5 information.

See `03_DATA/DOWNLOAD_SOURCES.md` for source locations, retrieval dates, query details and attribution.

## Data integrity

The official crop-yield table was reshaped from wide to long form and the selected wheat rows were converted to numeric values. No imputation, winsorization, smoothing or manual value correction was performed. The temperature series is used as lagged national climate context rather than local weather measurement.

## Data availability statement

The analysis-ready datasets supporting the study, together with their provenance, data dictionary, licensing information and audit notes, are publicly available in this repository:

https://github.com/hezejuyede/wheat-yield-reliability-audit
