import math
from fastapi import HTTPException, status


def validate_coordinates_range(latitude: float, longitude: float) -> None:
    """Validates that latitude and longitude are valid numeric coordinates."""
    if not (-90.0 <= latitude <= 90.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Latitude {latitude} is out of range [-90.0, 90.0].",
        )
    if not (-180.0 <= longitude <= 180.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Longitude {longitude} is out of range [-180.0, 180.0].",
        )
