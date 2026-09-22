"""
PRAVAH Digital Twin — GeoJSON & Catchment Service.
Ingests, enriches, and indexes catchment boundaries, drainage characteristics,
and sub-basins from PRAVAH's processed geospatial datasets.
"""

import csv
import json
import logging
import os
from typing import Any, Dict, List, Optional

from src.digital_twin.models.watershed import (
    Watershed,
    WatershedProperties,
    SubWatershed,
    WatershedListResponse,
)
from src.digital_twin.models.river_basin import RiverBasinSummary
from src.digital_twin.utils.geo_utils import (
    calculate_bbox,
    calculate_centroid,
    polygon_area_sqkm,
)

logger = logging.getLogger("pravah.digital_twin.geojson")


class GeoJsonService:
    """
    Central service for parsing and querying watershed boundaries, characteristics,
    and sub-basin relationships across Maharashtra Western Ghats and Northeast India.
    """

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            # Anchor to project root
            self.base_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..")
            )
        else:
            self.base_dir = base_dir

        self.watersheds_cache: Dict[str, Watershed] = {}
        self.geojson_features: List[Dict[str, Any]] = []
        self._load_datasets()

    def _load_datasets(self) -> None:
        """Load and merge metadata, characteristics, and GeoJSON boundaries."""
        metadata_path = os.path.join(self.base_dir, "data", "processed", "target_metadata.csv")
        characteristics_path = os.path.join(self.base_dir, "data", "processed", "target_catchment_characteristics.csv")
        catchments_geojson_path = os.path.join(self.base_dir, "data", "processed", "target_catchments.geojson")
        ne_geojson_path = os.path.join(self.base_dir, "data", "processed", "northeast", "northeast_candidate_catchments.geojson")
        ne_stations_path = os.path.join(self.base_dir, "data", "processed", "northeast", "station_catalog.csv")

        # 1. Ingest metadata map: GaugeID -> Row dict
        meta_by_gauge: Dict[str, Dict[str, str]] = {}
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        gid = row.get("GaugeID", "").strip()
                        meta_by_gauge[gid] = row
                        # Also index short numeric ID e.g. "585"
                        short_id = gid.replace("INDOFLOODS-gauge-", "").strip()
                        meta_by_gauge[short_id] = row
            except Exception as exc:
                logger.warning("Failed to parse target_metadata.csv: %s", exc)

        # 2. Ingest characteristics map: GaugeID -> Row dict
        char_by_gauge: Dict[str, Dict[str, str]] = {}
        if os.path.exists(characteristics_path):
            try:
                with open(characteristics_path, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        gid = row.get("GaugeID", "").strip()
                        char_by_gauge[gid] = row
                        short_id = gid.replace("INDOFLOODS-gauge-", "").strip()
                        char_by_gauge[short_id] = row
            except Exception as exc:
                logger.warning("Failed to parse target_catchment_characteristics.csv: %s", exc)

        # 3. Ingest Maharashtra target catchments GeoJSON
        if os.path.exists(catchments_geojson_path):
            try:
                with open(catchments_geojson_path, mode="r", encoding="utf-8") as f:
                    gj_data = json.load(f)
                    features = gj_data.get("features", [])
                    for feat in features:
                        props = feat.get("properties", {})
                        raw_gid = str(props.get("GaugeID") or props.get("_source_id") or "").strip()
                        full_gid = f"INDOFLOODS-gauge-{raw_gid}" if not raw_gid.startswith("INDOFLOODS") else raw_gid

                        meta = meta_by_gauge.get(raw_gid, {}) or meta_by_gauge.get(full_gid, {})
                        char = char_by_gauge.get(raw_gid, {}) or char_by_gauge.get(full_gid, {})

                        geom = feat.get("geometry", {})
                        coords = geom.get("coordinates", [])
                        centroid_lat, centroid_lon = calculate_centroid(coords)
                        bbox = calculate_bbox(coords)

                        # Parse drainage characteristics
                        def _flt(v: Any, default: float) -> float:
                            try:
                                return float(v) if v not in (None, "") else default
                            except (ValueError, TypeError):
                                return default

                        drainage_area = _flt(char.get("Drainage Area"), _flt(meta.get("Catchment Area"), 850.0))
                        relief_m = _flt(char.get("Catchment Relief"), 750.0)
                        stream_order = int(_flt(char.get("Stream Order"), 3.0))
                        drainage_density = _flt(char.get("Drainage Density"), 0.00015)
                        soil_type = char.get("Soil type") or "Vertisols"
                        land_cover = char.get("Land cover") or "Mosaic vegetation"
                        river_name = meta.get("River Name/ Tributory/ SubTributory") or "Krishna"
                        station_name = meta.get("Station") or f"Station {raw_gid}"
                        basin_name = meta.get("Basin") or "Krishna"
                        warning_m = _flt(meta.get("Warning Level"), 540.0)
                        danger_m = _flt(meta.get("Danger Level"), 542.0)

                        # Determine default SCS Curve Number (AMC II)
                        cn_val = 72.0
                        if "Vertisols" in soil_type:
                            cn_val = 78.0
                        elif "Leptosols" in soil_type:
                            cn_val = 82.0
                        if "Cropland" in land_cover:
                            cn_val += 3.0

                        # Create sub-watersheds breakdown
                        sub_units: List[SubWatershed] = [
                            SubWatershed(
                                sub_id=f"{raw_gid}_UPPER",
                                name=f"{station_name} Upper Catchment",
                                drainage_area_sqkm=round(drainage_area * 0.45, 2),
                                stream_order=max(1, stream_order - 1),
                                mean_elevation_m=round(relief_m * 0.75, 1),
                                slope_deg=14.5,
                                flow_destination_id=f"{raw_gid}_LOWER",
                            ),
                            SubWatershed(
                                sub_id=f"{raw_gid}_LOWER",
                                name=f"{station_name} Riparian Valley",
                                drainage_area_sqkm=round(drainage_area * 0.55, 2),
                                stream_order=stream_order,
                                mean_elevation_m=round(relief_m * 0.35, 1),
                                slope_deg=4.2,
                                flow_destination_id=None,
                            )
                        ]

                        ws_props = WatershedProperties(
                            watershed_id=full_gid,
                            gauge_id=full_gid,
                            station_name=station_name,
                            river_name=river_name,
                            basin_name=basin_name,
                            state="Maharashtra",
                            drainage_area_sqkm=round(drainage_area, 2),
                            perimeter_km=round(_flt(char.get("Catchment Perimeter"), 120000.0) / 1000.0, 2),
                            relief_m=round(relief_m, 1),
                            mean_elevation_m=round(_flt(char.get("Annual Mean Temperature"), 24.5) * 20.0 + 350.0, 1),
                            max_flow_length_km=round(_flt(char.get("Maximal Flow Length"), 35000.0) / 1000.0, 2),
                            stream_order=stream_order,
                            drainage_density=round(drainage_density, 6),
                            soil_type=soil_type,
                            land_cover=land_cover,
                            curve_number_amc2=round(cn_val, 1),
                            time_of_concentration_hr=round(max(1.5, drainage_area ** 0.38 / 2.0), 2),
                            warning_level_m=warning_m if warning_m > 0 else None,
                            danger_level_m=danger_m if danger_m > 0 else None,
                            centroid_lat=centroid_lat,
                            centroid_lon=centroid_lon,
                            bbox=bbox,
                        )

                        ws_obj = Watershed(
                            id=full_gid,
                            properties=ws_props,
                            geometry=geom,
                            sub_watersheds=sub_units,
                        )

                        self.watersheds_cache[full_gid] = ws_obj
                        self.watersheds_cache[raw_gid] = ws_obj

                        # Store rich GeoJSON feature
                        feat_rich = {
                            "type": "Feature",
                            "id": full_gid,
                            "properties": ws_props.model_dump(),
                            "geometry": geom,
                        }
                        self.geojson_features.append(feat_rich)
            except Exception as exc:
                logger.error("Failed to load target_catchments.geojson: %s", exc)

        # 4. Ingest Northeast candidate catchments
        if os.path.exists(ne_geojson_path):
            try:
                with open(ne_geojson_path, mode="r", encoding="utf-8") as f:
                    ne_gj = json.load(f)
                    for feat in ne_gj.get("features", []):
                        p = feat.get("properties", {})
                        st_name = p.get("station_name") or p.get("station_id") or "NE Station"
                        clean_id = f"NE-{st_name.replace(' ', '_')}"
                        geom = feat.get("geometry", {})
                        coords = geom.get("coordinates", [])
                        c_lat, c_lon = calculate_centroid(coords)
                        bbox = calculate_bbox(coords)
                        sub_area = float(p.get("SUB_AREA") or 350.0)

                        ws_props = WatershedProperties(
                            watershed_id=clean_id,
                            gauge_id=clean_id,
                            station_name=st_name,
                            river_name="Brahmaputra / Tributaries",
                            basin_name="Brahmaputra",
                            state="Assam",
                            drainage_area_sqkm=round(sub_area, 2),
                            perimeter_km=round(sub_area * 0.4, 2),
                            relief_m=1250.0,
                            mean_elevation_m=180.0,
                            max_flow_length_km=round(sub_area * 0.15, 2),
                            stream_order=4,
                            drainage_density=0.00021,
                            soil_type="Alluvial / Silty Loam",
                            land_cover="Wetlands / Tea Plantations",
                            curve_number_amc2=81.0,
                            time_of_concentration_hr=round(max(2.0, sub_area ** 0.38 / 2.0), 2),
                            warning_level_m=50.0,
                            danger_level_m=52.5,
                            centroid_lat=c_lat,
                            centroid_lon=c_lon,
                            bbox=bbox,
                        )

                        ws_obj = Watershed(
                            id=clean_id,
                            properties=ws_props,
                            geometry=geom,
                            sub_watersheds=[],
                        )
                        self.watersheds_cache[clean_id] = ws_obj
                        feat_rich = {
                            "type": "Feature",
                            "id": clean_id,
                            "properties": ws_props.model_dump(),
                            "geometry": geom,
                        }
                        self.geojson_features.append(feat_rich)
            except Exception as exc:
                logger.warning("Failed to load northeast_candidate_catchments.geojson: %s", exc)

        logger.info("Loaded %d unique watershed units in Digital Twin GeoJsonService", len(self.watersheds_cache))

    def get_all_watersheds(self) -> List[WatershedProperties]:
        """Return list of distinct watershed metadata properties."""
        seen = set()
        distinct: List[WatershedProperties] = []
        for ws in self.watersheds_cache.values():
            if ws.id not in seen:
                seen.add(ws.id)
                distinct.append(ws.properties)
        return sorted(distinct, key=lambda w: (w.state, w.basin_name, w.station_name))

    def get_watershed_by_id(self, watershed_id: str) -> Optional[Watershed]:
        """Lookup a watershed by full ID or short ID."""
        clean_id = watershed_id.strip()
        if clean_id in self.watersheds_cache:
            return self.watersheds_cache[clean_id]

        full_id = f"INDOFLOODS-gauge-{clean_id}"
        if full_id in self.watersheds_cache:
            return self.watersheds_cache[full_id]

        short_id = clean_id.replace("INDOFLOODS-gauge-", "")
        if short_id in self.watersheds_cache:
            return self.watersheds_cache[short_id]

        return None

    def get_geojson_feature_collection(self) -> Dict[str, Any]:
        """Return complete GeoJSON FeatureCollection of all watershed boundaries."""
        # Deduplicate features by id
        seen = set()
        deduped = []
        for feat in self.geojson_features:
            fid = feat.get("id")
            if fid not in seen:
                seen.add(fid)
                deduped.append(feat)

        return {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
            "features": deduped,
        }

    def get_river_basins_summary(self) -> List[RiverBasinSummary]:
        """Aggregate monitored watersheds into primary river basins."""
        basin_map: Dict[str, Dict[str, Any]] = {}
        for ws in self.watersheds_cache.values():
            p = ws.properties
            b_key = f"{p.state}_{p.basin_name}"
            if b_key not in basin_map:
                basin_map[b_key] = {
                    "basin_id": f"BASIN_{p.basin_name.upper().replace(' ', '_')}",
                    "basin_name": p.basin_name,
                    "region": f"{p.state} Region",
                    "total_area_sqkm": 0.0,
                    "main_rivers": set(),
                    "tributaries": set(),
                    "stations": set(),
                    "watershed_ids": set(),
                }

            basin_map[b_key]["total_area_sqkm"] += p.drainage_area_sqkm
            basin_map[b_key]["main_rivers"].add(p.river_name.split("/")[0].strip())
            if "/" in p.river_name:
                for part in p.river_name.split("/")[1:]:
                    basin_map[b_key]["tributaries"].add(part.strip())
            basin_map[b_key]["stations"].add(p.station_name)
            basin_map[b_key]["watershed_ids"].add(p.watershed_id)

        summaries: List[RiverBasinSummary] = []
        for b_dict in basin_map.values():
            summaries.append(
                RiverBasinSummary(
                    basin_id=b_dict["basin_id"],
                    basin_name=b_dict["basin_name"],
                    region=b_dict["region"],
                    total_area_sqkm=round(b_dict["total_area_sqkm"], 2),
                    main_rivers=sorted(list(b_dict["main_rivers"])),
                    tributaries=sorted(list(b_dict["tributaries"])),
                    station_count=len(b_dict["stations"]),
                    active_watersheds=sorted(list(b_dict["watershed_ids"])),
                )
            )
        return sorted(summaries, key=lambda s: s.total_area_sqkm, reverse=True)
