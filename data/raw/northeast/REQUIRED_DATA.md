# Northeast data intake

The attached rainfall and water-level sources are already integrated. Add the remaining Maharashtra-equivalent sources in these folders:

- `flood_events/`: the supplied India Flood Inventory is stored here for historical context. Add verified station-level events with `StationID`, `Start Date`, `End Date`, and `Flood Type` or threshold-derived labels.
- `catchments/`: HydroBASINS Asia level-12 candidate polygons are downloaded and matched to stations. Replace or verify them with gauge-specific upstream polygons before final training.
- `static_features/`: candidate basin area/upstream area features are generated. Add DEM, slope, drainage, soil, land cover, lithology, population, and infrastructure features for the complete Maharashtra-equivalent schema.

Do not add district-only impact summaries as station labels. The training pipeline will remain blocked until flood events, catchments, and static features can be joined to the station catalog.
