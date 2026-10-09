import math
import logging
from typing import Optional

from app.core.config import settings
from app.core.constants import LocationValidationStatus

logger = logging.getLogger(__name__)


class LocationService:
    @staticmethod
    def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great-circle distance between two points on Earth in meters.
        """
        r = 6371000.0  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2.0) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return round(r * c, 2)

    @classmethod
    def is_within_civic_boundary(cls, latitude: float, longitude: float) -> bool:
        """
        Checks if given coordinates fall inside the configured civic target bounding box.
        """
        return (
            settings.civic_lat_min <= latitude <= settings.civic_lat_max
            and settings.civic_lon_min <= longitude <= settings.civic_lon_max
        )

    @classmethod
    def validate_location(
        cls,
        submitted_lat: float,
        submitted_lon: float,
        exif_lat: Optional[float] = None,
        exif_lon: Optional[float] = None,
    ) -> dict:
        """
        Validates submitted location and compares with photo EXIF location.
        Returns:
            {
                "status": LocationValidationStatus,
                "distance_meters": Optional[float],
                "within_boundary": bool,
                "message": str
            }
        """
        # Validate earth coordinates
        if not (-90.0 <= submitted_lat <= 90.0 and -180.0 <= submitted_lon <= 180.0):
            return {
                "status": LocationValidationStatus.INVALID,
                "distance_meters": None,
                "within_boundary": False,
                "message": "Submitted coordinates are invalid.",
            }

        within_boundary = cls.is_within_civic_boundary(submitted_lat, submitted_lon)

        # If photo does not contain EXIF GPS
        if exif_lat is None or exif_lon is None:
            return {
                "status": LocationValidationStatus.MISSING_METADATA,
                "distance_meters": None,
                "within_boundary": within_boundary,
                "message": f"Photo lacks GPS metadata. Submitted coordinates are {'inside' if within_boundary else 'outside'} {settings.civic_target_city} boundary.",
            }

        # Check EXIF coordinates sanity
        if not (-90.0 <= exif_lat <= 90.0 and -180.0 <= exif_lon <= 180.0):
            return {
                "status": LocationValidationStatus.INVALID,
                "distance_meters": None,
                "within_boundary": within_boundary,
                "message": "Photo EXIF coordinates are malformed.",
            }

        # Both locations available: compute discrepancy
        distance = cls.haversine_distance_meters(submitted_lat, submitted_lon, exif_lat, exif_lon)
        threshold = settings.location_discrepancy_threshold_meters

        if distance > threshold:
            return {
                "status": LocationValidationStatus.FLAGGED_FOR_REVIEW,
                "distance_meters": distance,
                "within_boundary": within_boundary,
                "message": f"Submitted location differs from photo EXIF location by {distance:.1f}m (threshold: {threshold:.1f}m).",
            }

        if not within_boundary:
            return {
                "status": LocationValidationStatus.FLAGGED_FOR_REVIEW,
                "distance_meters": distance,
                "within_boundary": False,
                "message": f"Location is outside configured {settings.civic_target_city} jurisdiction.",
            }

        return {
            "status": LocationValidationStatus.VALID,
            "distance_meters": distance,
            "within_boundary": True,
            "message": f"Location verified within {settings.civic_target_city} jurisdiction and matches photo EXIF.",
        }
