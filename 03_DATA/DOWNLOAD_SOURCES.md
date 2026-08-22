# Download sources and queries

## 1. Regional crop yield

- Dataset: Урожайность сельскохозяйственных культур по территории / Crops' yield by territory
- Publisher: National Statistical Committee of the Kyrgyz Republic, Department of Agricultural Statistics
- Official dynamic download: https://stat.gov.kg/ru/statistics/download/dynamic/1272/
- Open-data metadata: https://data.gov.kg/ru/dataset/ypoxanhoctb-cejibckoxo3rnctbehhbix-kyjibtyp-no-teppntopnn
- Version: 1.1 on the open-data portal
- Update shown at retrieval: 2026-03-02
- Retrieval date: 2026-07-30
- Query: complete dynamic table; seven oblast rows; wheat yield; annual columns 1991-2025
- Licence: Creative Commons Attribution according to the open-data portal

## 2. Annual temperature anomalies

- Dataset: Annual temperature anomalies
- Publisher/processor: Our World in Data; adapted from modified Copernicus Climate Change Service ERA5 information
- CSV query: https://ourworldindata.org/grapher/annual-temperature-anomalies.csv?v=1&csvType=full&useColumnShortNames=false
- Metadata: https://ourworldindata.org/grapher/annual-temperature-anomalies.metadata.json?v=1&csvType=full&useColumnShortNames=false
- Archive cited by the data page: 2026-07-27 archive
- Retrieval date: 2026-07-30
- Query: Entity = Kyrgyzstan; years 1991-2025; annual 2-m temperature anomaly relative to 1991-2020
- Licence: OWID-produced data/visualization under CC BY; original Copernicus terms must also be respected

`04_CODE/download_data.py` re-downloads these sources. The legacy XLS is bundled in the submission reproducibility package together with a lossless LibreOffice-converted XLSX to avoid reader compatibility failures.
