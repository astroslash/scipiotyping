from __future__ import annotations

import re

import pytest

from scipiotyping import create_app


@pytest.fixture()
def app(tmp_path):
    return create_app({"TESTING": True, "SECRET_KEY": "test-key", "DATABASE": str(tmp_path / "test.db")})


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def csrf(client):
    response = client.get("/")
    return re.search(rb'name="csrf-token" content="([^"]+)"', response.data).group(1).decode()

