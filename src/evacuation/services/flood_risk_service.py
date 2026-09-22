"""Flood risk zone management and spatial risk mapping."""
from typing import List, Dict, Any
from src.evacuation.models.risk_zone import RiskZone, RiskLevel


class FloodRiskService:
    """Maintains spatial flood risk zones and calculates hazard exposure."""

    def __init__(self):
        self._risk_zones: List[RiskZone] = self._seed_risk_zones()

    def _seed_risk_zones(self) -> List[RiskZone]:
        """Pre-seeds realistic hydrological risk zones across critical river corridors."""
        return [
            RiskZone(
                zone_id="ZONE-PUNE-01",
                name="Mula-Mutha Confluence Floodplain",
                basin="Mula-Mutha",
                risk_level=RiskLevel.HIGH,
                risk_score=0.72,
                inundation_depth_m=1.4,
                polygon=[
                    [18.5150, 73.8400],
                    [18.5350, 73.8400],
                    [18.5350, 73.8750],
                    [18.5150, 73.8750],
                ],
            ),
            RiskZone(
                zone_id="ZONE-KARAD-01",
                name="Krishna-Koyna Confluence Inundation Sector",
                basin="Krishna",
                risk_level=RiskLevel.EXTREME,
                risk_score=0.88,
                inundation_depth_m=2.2,
                polygon=[
                    [17.2750, 74.1650],
                    [17.3050, 74.1650],
                    [17.3050, 74.2050],
                    [17.2750, 74.2050],
                ],
            ),
            RiskZone(
                zone_id="ZONE-MAHAD-01",
                name="Savitri River Low-Lying Corridor",
                basin="Savitri",
                risk_level=RiskLevel.HIGH,
                risk_score=0.68,
                inundation_depth_m=1.8,
                polygon=[
                    [18.0650, 73.4050],
                    [18.0950, 73.4050],
                    [18.0950, 73.4450],
                    [18.0650, 73.4450],
                ],
            ),
            RiskZone(
                zone_id="ZONE-CHIPLUN-01",
                name="Vashishti River Valley Floodway",
                basin="Vashishti",
                risk_level=RiskLevel.MODERATE,
                risk_score=0.45,
                inundation_depth_m=0.9,
                polygon=[
                    [17.5150, 73.5050],
                    [17.5450, 73.5050],
                    [17.5450, 73.5450],
                    [17.5150, 73.5450],
                ],
            ),
            RiskZone(
                zone_id="ZONE-KOLHAPUR-01",
                name="Panchganga Basin Lowland Basin",
                basin="Panchganga",
                risk_level=RiskLevel.HIGH,
                risk_score=0.65,
                inundation_depth_m=1.5,
                polygon=[
                    [16.6950, 74.2250],
                    [16.7350, 74.2250],
                    [16.7350, 74.2650],
                    [16.6950, 74.2650],
                ],
            ),
            RiskZone(
                zone_id="ZONE-GUWAHATI-01",
                name="Brahmaputra Waterfront & Bharalu Channel",
                basin="Brahmaputra",
                risk_level=RiskLevel.EXTREME,
                risk_score=0.82,
                inundation_depth_m=2.0,
                polygon=[
                    [26.1750, 91.7350],
                    [26.2050, 91.7350],
                    [26.2050, 91.7850],
                    [26.1750, 91.7850],
                ],
            ),
        ]

    def get_all_risk_zones(self) -> List[RiskZone]:
        """Returns list of active flood risk zones."""
        return self._risk_zones

    def get_risk_zones_geojson(self) -> Dict[str, Any]:
        """Returns GeoJSON FeatureCollection of flood zones for Leaflet overlay."""
        features = []
        for z in self._risk_zones:
            # Leaflet polygon expects [[lng, lat], ...] for standard GeoJSON
            geojson_poly = [[[pt[1], pt[0]] for pt in z.polygon]]
            # Close polygon
            if geojson_poly[0][0] != geojson_poly[0][-1]:
                geojson_poly[0].append(geojson_poly[0][0])

            features.append({
                "type": "Feature",
                "properties": {
                    "zone_id": z.zone_id,
                    "name": z.name,
                    "basin": z.basin,
                    "risk_level": z.risk_level.value,
                    "risk_score": z.risk_score,
                    "inundation_depth_m": z.inundation_depth_m,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": geojson_poly,
                },
            })
        return {
            "type": "FeatureCollection",
            "features": features,
        }


flood_risk_service = FloodRiskService()
