"""
Ward Assignment Service.

Architecture for automatic ward assignment from coordinates (latitude, longitude)
using point-in-polygon matching against official ward boundary GeoJSON files.
DO NOT fabricate or guess boundary mappings; if no official polygon dataset is loaded,
the service returns None or preserves provided administrative ward data cleanly.
"""

from typing import Optional, List, Dict, Any
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class WardService:
    _boundaries_cache: Optional[List[Dict[str, Any]]] = None
    _boundaries_loaded: bool = False

    @classmethod
    def _load_boundaries(cls) -> List[Dict[str, Any]]:
        """
        Loads official ward boundaries from configured GeoJSON file if present.
        """
        if cls._boundaries_loaded:
            return cls._boundaries_cache or []

        cls._boundaries_loaded = True
        custom_path = os.getenv("WARD_BOUNDARIES_GEOJSON_PATH")
        default_path = Path(__file__).resolve().parent.parent / "data" / "ward_boundaries.geojson"
        target_path = Path(custom_path) if custom_path else default_path

        if not target_path.exists():
            logger.info("No official ward boundary GeoJSON found at %s. Ward assignment ready for official dataset.", target_path)
            cls._boundaries_cache = []
            return []

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                features = data.get("features", [])
                cls._boundaries_cache = features
                logger.info("Loaded %d official ward boundaries from %s", len(features), target_path)
                return cls._boundaries_cache
        except Exception as e:
            logger.error("Error loading ward boundaries from %s: %s", target_path, e)
            cls._boundaries_cache = []
            return []

    @classmethod
    def _point_in_polygon(cls, x: float, y: float, polygon_coords: List[List[float]]) -> bool:
        """
        Standard ray-casting algorithm to test if point (x=lon, y=lat) is inside polygon.
        """
        n = len(polygon_coords)
        inside = False
        p1x, p1y = polygon_coords[0]
        for i in range(n + 1):
            p2x, p2y = polygon_coords[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    @classmethod
    def assign_ward(cls, latitude: float, longitude: float) -> Optional[str]:
        """
        Determines the official civic ward from coordinates using point-in-polygon.
        Returns ward name/identifier string if an official polygon contains the point,
        or None if no official boundary matched or dataset is not configured.
        """
        features = cls._load_boundaries()
        if not features:
            return None

        # Point in GeoJSON is [longitude, latitude]
        px, py = longitude, latitude

        for feat in features:
            geom = feat.get("geometry", {})
            geom_type = geom.get("type", "")
            coords = geom.get("coordinates", [])
            properties = feat.get("properties", {})
            ward_name = properties.get("ward_name") or properties.get("ward") or properties.get("name")

            if not ward_name:
                continue

            if geom_type == "Polygon":
                for ring in coords:
                    if cls._point_in_polygon(px, py, ring):
                        return str(ward_name)
            elif geom_type == "MultiPolygon":
                for poly in coords:
                    for ring in poly:
                        if cls._point_in_polygon(px, py, ring):
                            return str(ward_name)

        return None
