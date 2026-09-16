import pytest

import database.db
from app import app as flask_app
from database.db import init_db, seed_db


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    """Point every DB call at a fresh per-test SQLite file.

    get_db() reads the module-level DB_PATH at call time, so rebinding it
    redirects init_db(), seed_db(), the user helpers, and any query a route
    makes under the test client. Together with app.py keeping its own
    init_db()/seed_db() inside the __main__ guard, this keeps the real
    expense_tracker.db out of the suite entirely — importing app creates
    nothing — and makes repeated pytest runs idempotent.
    """
    monkeypatch.setattr(database.db, "DB_PATH", str(tmp_path / "test.db"))
    init_db()
    seed_db()
    yield


@pytest.fixture
def app():
    flask_app.config.update({"TESTING": True})
    yield flask_app
