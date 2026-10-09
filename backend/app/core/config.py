from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    app_name: str
    app_version: str
    debug: bool

    # Database
    database_url: str

    # JWT
    jwt_secret_key: str = "civic-intelligence-secret-key-32-chars-long-4302"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS
    cors_origins: list[str] = ["*"]

    # Storage
    upload_dir: str = "uploads"
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10 MB

    # Location / Geofence (Civic Target Area: e.g. Pune Urban Region)
    civic_target_city: str = "Pune"
    civic_lat_min: float = 18.25
    civic_lat_max: float = 18.75
    civic_lon_min: float = 73.65
    civic_lon_max: float = 74.15
    location_discrepancy_threshold_meters: float = 500.0  # discrepancy between EXIF and submitted GPS

    # Email
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = ""
    mail_port: int = 587
    mail_server: str = "smtp.gmail.com"
    mail_from_name: str = "Civic Intelligence Platform"

    # Cloudinary
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    # AI
    ai_model_path: str = ""

    model_config = SettingsConfigDict(
        env_file=(
            str(Path(__file__).resolve().parent.parent.parent / ".env"),
            ".env",
        ),
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()