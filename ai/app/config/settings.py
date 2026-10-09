from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "Civic Intelligence AI Service"
    app_version: str = "0.1.0"


settings = Settings()
