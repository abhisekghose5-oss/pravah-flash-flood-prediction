# Northeast external data sources

These sources are selected for the missing Northeast layers. Downloaded files are stored under `data/raw/northeast/external/`.

## Added

- NRSC/ISRO, *Flood Hazard Zonation Atlas of Assam using multi-sensor satellite data 1998-2023*: `data/raw/northeast/external/Flood_Hazard_Zonation_Atlas_Assam_1998_2023.pdf`

This atlas is a regional hazard/context source. It is not a station-day target table and must not be used directly as `target_onset` or `target_active` labels.

## Required portal downloads

- CWC/India-WRIS hydrological observations: https://indiawris.gov.in/wris/
- CWC classified hydrological data release: https://cdrc.cwc.gov.in/
- Assam Water Resources hydrological data and daily flood bulletins: https://waterresources.assam.gov.in/information-services/hydrological-data
- Assam State Disaster Management Authority flood reports: https://asdma.assam.gov.in/resource/assam-flood-report
- HydroSHEDS/HydroBASINS catchment boundaries and river networks: https://www.hydrosheds.org/products

The project currently uses HydroBASINS Asia level 12 as a candidate polygon source. It is spatially matched to the 46 station points, but it is not a gauge-specific upstream delineation.

The CWC/ASDMA sources require portal access or a manual download selection. HydroSHEDS data must be selected at a resolution appropriate for the gauge catchments. After download, place station-linked event data in `data/raw/northeast/flood_events/`, polygons in `data/raw/northeast/catchments/`, and derived static features in `data/raw/northeast/static_features/`.
