import os
from uuid import uuid4

import pytest
from sitewatch.config import Settings
from sitewatch.database import Database
from sitewatch.models import Base
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


@pytest.fixture
def context(tmp_path):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to an isolated PostgreSQL database ending in _test")
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("Integration tests require a database name ending in _test")
    schema = "test_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as db:
        db.execute(text(f'CREATE SCHEMA "{schema}"'))
    settings = Settings(database_url=url, data_dir=tmp_path, model_path=tmp_path / "model.pt")
    database = Database(settings)
    database.engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    from sqlalchemy.orm import sessionmaker

    database.session = sessionmaker(database.engine, expire_on_commit=False)
    Base.metadata.create_all(database.engine)
    database.prepare()
    try:
        yield settings, database
    finally:
        database.engine.dispose()
        with admin.begin() as db:
            db.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
