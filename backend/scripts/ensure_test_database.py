"""Create civic_db_test if it does not exist; never alters another database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.core.config import settings


database_url = make_url(settings.database_url)
if database_url.database != "civic_db_test":
    raise SystemExit("Refusing to initialize a database other than civic_db_test")

maintenance_url = database_url.set(database="postgres")
engine = create_engine(maintenance_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
try:
    with engine.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": "civic_db_test"},
        ).scalar()
        if not exists:
            connection.exec_driver_sql('CREATE DATABASE "civic_db_test"')
            print("Created civic_db_test")
        else:
            print("civic_db_test already exists")
finally:
    engine.dispose()
