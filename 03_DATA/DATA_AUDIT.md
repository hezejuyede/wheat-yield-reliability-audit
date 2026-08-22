# Data audit

- Crop-yield source file SHA256: `b5dbf9d645244c11100b58c5f3f6587f8407ce9baa163071cc32cbe6bae122b9`
- Converted XLSX SHA256: `987a2d60d5aea0f8303af0f9ab7a9dd32ed3350178ac6841e18852e8bfd0d78b`
- Temperature CSV SHA256: `b49073e5e3e174a9474999af366a3ec36e8479fae6fc764e2a90a0875e2d5a33`
- Crop-yield coverage selected: seven oblasts × 35 years = 245 raw observations, 1991-2025.
- Temperature coverage used: Kyrgyzstan, 1991-2025.
- Analysis panel: 224 region-years, 1994-2025, after constructing three-year lagged features.
- Missing target values in selected crop rows: 0.
- Missing predictor values in the final panel: 0.
- Unit: one centner per hectare = 100 kg per hectare.
- Cleaning: the official wide table was reshaped to long form; selected wheat rows were converted to numeric; no imputation, winsorization, smoothing or manual value correction was performed.
- Time availability: every target-year feature ends at t-1. Country annual temperature is used as a lagged national context variable, not as a local weather measurement.
- Geographic limitation: no region-level precipitation, soil, irrigation, cultivar, fertilizer or management variables are available in the two-source design. Causal climate attribution is therefore not claimed.

## Climate-source decision audit

A regional NASA POWER daily-weather route was tested during the final evidence audit to address the spatial resolution limitation. The endpoint could not be retrieved and rebuilt reliably in the working environment within the bounded workflow. No values from that attempt were inserted. The final analysis therefore retains the directly downloadable OWID/Copernicus ERA5 national annual anomaly series, treats it only as lagged climate context, and explicitly excludes local-weather and causal climate claims.
