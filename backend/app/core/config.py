from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    # Application
    app_name: str
    app_version: str
    debug: bool = False

    # Database
    database_url: str

    # JWT
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS
    cors_origins: list[str] = [
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:5001",
        "http://127.0.0.1:5001",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]

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

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_mode(cls, value):
        # Some launch environments export DEBUG=release. Pydantic does not
        # interpret that as a boolean, so normalize the common build modes.
        if isinstance(value, str) and value.lower() in {"release", "production", "prod"}:
            return False
        if isinstance(value, str) and value.lower() in {"debug", "development", "dev"}:
            return True
        return value

    @field_validator("database_url")
    @classmethod
    def force_test_database(cls, value: str) -> str:
        """Hard-scope every backend/Alembic connection to the disposable test DB."""
        url = make_url(value)
        if not url.password:
            raise ValueError("DATABASE_URL must include a password for civic_user")
        return url.set(
            drivername="postgresql+psycopg",
            username="civic_user",
            host="127.0.0.1",
            port=5432,
            database="civic_db_test",
        ).render_as_string(hide_password=False)

    model_config = SettingsConfigDict(
        env_file=(
            str(Path(__file__).resolve().parent.parent.parent / ".env"),
            ".env",
        ),
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
