def detect_ward(latitude: float, longitude: float) -> dict[str, str]:
    return {"ward": "unknown", "coordinates": f"{latitude},{longitude}"}
