import io
import logging
from datetime import datetime, timezone
from typing import Any, Optional, Tuple
from PIL import Image, ExifTags

logger = logging.getLogger(__name__)


class ExifService:
    @staticmethod
    def _convert_dms_to_degrees(dms_values: Any, ref: Optional[str]) -> Optional[float]:
        """Convert EXIF degrees, minutes, seconds tuple/rational to decimal degrees."""
        try:
            if not dms_values or len(dms_values) < 3:
                return None

            degrees = float(dms_values[0])
            minutes = float(dms_values[1])
            seconds = float(dms_values[2])

            decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
            if ref and ref.upper() in ["S", "W"]:
                decimal = -decimal
            return round(decimal, 6)
        except Exception as e:
            logger.debug(f"Error converting DMS to degrees: {e}")
            return None

    @classmethod
    def extract_exif(cls, image_source: str | bytes) -> dict:
        """
        Extracts GPS coordinates and timestamp from an image path or bytes.
        Returns coordinates, timestamp, and status ('VALID' or 'MISSING_METADATA').
        Never throws on corrupt or missing metadata.
        """
        result = {
            "has_gps": False,
            "latitude": None,
            "longitude": None,
            "timestamp": None,
            "status": "MISSING_METADATA",
        }

        try:
            if isinstance(image_source, bytes):
                img = Image.open(io.BytesIO(image_source))
            else:
                img = Image.open(image_source)

            exif_data = img.getexif()
            if not exif_data:
                return result

            # Parse datetime
            date_str = exif_data.get(0x9003) or exif_data.get(0x0132)  # DateTimeOriginal or DateTime
            if date_str and isinstance(date_str, str):
                for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                    try:
                        result["timestamp"] = datetime.strptime(date_str.strip(), fmt).replace(
                            tzinfo=timezone.utc
                        )
                        break
                    except ValueError:
                        continue

            # Look for GPS info in IFD or root
            gps_ifd = None
            try:
                # Pillow 10+ uses get_ifd
                gps_ifd = exif_data.get_ifd(ExifTags.IFD.GPSInfo)
            except Exception:
                pass

            if not gps_ifd:
                # Fallback to tag 34853 (0x8825)
                gps_info_raw = exif_data.get(0x8825)
                if isinstance(gps_info_raw, dict):
                    gps_ifd = gps_info_raw

            if not gps_ifd:
                return result

            # GPS tag mappings
            # 1: GPSLatitudeRef, 2: GPSLatitude, 3: GPSLongitudeRef, 4: GPSLongitude
            lat_ref = gps_ifd.get(1)
            lat_raw = gps_ifd.get(2)
            lon_ref = gps_ifd.get(3)
            lon_raw = gps_ifd.get(4)

            if lat_raw and lon_raw:
                lat = cls._convert_dms_to_degrees(lat_raw, lat_ref)
                lon = cls._convert_dms_to_degrees(lon_raw, lon_ref)

                if lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180:
                    result["has_gps"] = True
                    result["latitude"] = lat
                    result["longitude"] = lon
                    result["status"] = "VALID"

        except Exception as e:
            logger.warning(f"EXIF extraction exception encountered: {e}")

        return result
