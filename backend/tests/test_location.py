from app.core.constants import LocationValidationStatus
from app.services.exif_service import ExifService
from app.services.location_service import LocationService


def test_haversine_distance():
    # Pune Station (18.5284, 73.8739) to Shaniwar Wada (18.5196, 73.8553) ~2.2 km
    dist = LocationService.haversine_distance_meters(18.5284, 73.8739, 18.5196, 73.8553)
    assert 2000 < dist < 2500


def test_location_missing_exif():
    # When citizen submits location but photo has no EXIF
    result = LocationService.validate_location(
        submitted_lat=18.5204,
        submitted_lon=73.8567,
        exif_lat=None,
        exif_lon=None,
    )
    assert result["status"] == LocationValidationStatus.MISSING_METADATA
    assert result["within_boundary"] is True


def test_location_valid_matching_exif():
    # Both locations within 100 meters
    result = LocationService.validate_location(
        submitted_lat=18.5204,
        submitted_lon=73.8567,
        exif_lat=18.5205,
        exif_lon=73.8568,
    )
    assert result["status"] == LocationValidationStatus.VALID
    assert result["distance_meters"] is not None
    assert result["distance_meters"] < 50


def test_location_discrepant_exif_flags_for_review():
    # 2km discrepancy (exceeds default 500m threshold)
    result = LocationService.validate_location(
        submitted_lat=18.5204,
        submitted_lon=73.8567,
        exif_lat=18.5400,
        exif_lon=73.8700,
    )
    assert result["status"] == LocationValidationStatus.FLAGGED_FOR_REVIEW
    assert result["distance_meters"] > 500


def test_location_invalid_coordinates():
    result = LocationService.validate_location(
        submitted_lat=999.0,
        submitted_lon=73.8567,
    )
    assert result["status"] == LocationValidationStatus.INVALID


def test_exif_extraction_no_crash_on_clean_image(sample_image_bytes):
    # A cleanly synthesized PIL image has no EXIF
    exif = ExifService.extract_exif(sample_image_bytes)
    assert exif["has_gps"] is False
    assert exif["status"] == "MISSING_METADATA"
    assert exif["latitude"] is None
