from sqlalchemy.engine import make_url

from app.core.config import Settings


def test_application_database_url_is_always_pinned_to_test_database():
    settings = Settings(
        app_name="Test",
        app_version="1",
        database_url="postgresql://civic_user:secret-placeholder@remote.example:9999/civic_db",
        jwt_secret_key="x" * 32,
    )
    url = make_url(settings.database_url)
    assert url.database == "civic_db_test"
    assert url.username == "civic_user"
    assert url.host == "127.0.0.1"
    assert url.port == 5432


def test_development_cors_defaults_do_not_allow_every_origin():
    settings = Settings(
        app_name="Test",
        app_version="1",
        database_url="postgresql://civic_user:secret-placeholder@localhost/civic_db_test",
        jwt_secret_key="x" * 32,
    )
    assert "*" not in settings.cors_origins
    assert "http://localhost:5000" in settings.cors_origins
    assert "http://127.0.0.1:5001" in settings.cors_origins
