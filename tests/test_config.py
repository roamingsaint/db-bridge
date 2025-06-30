# tests/test_config.py

import pytest

from db_bridge.config import load_config


@pytest.fixture(autouse=True)
def tmp_config(tmp_path, monkeypatch):
    # Create a temp INI file
    ini_path = tmp_path / "test_config.ini"
    INI = """
[DEFAULT]
active = alpha

[alpha]
driver   = sqlite
database = /tmp/alpha.db

[bravo]
driver   = mysql
host     = localhost
port     = 3306
database = bravo_db
user     = user
password = pass
"""
    # Write the INI content directly
    ini_path.write_text(INI)
    # Point the loader at it
    monkeypatch.setenv("DB_BRIDGE_CONFIG", str(ini_path))
    return ini_path


def test_load_default():
    creds = load_config()
    assert creds["driver"] == "sqlite"
    assert creds["database"] == "/tmp/alpha.db"


def test_load_named_profile():
    creds = load_config("bravo")
    assert creds["driver"] == "mysql"
    assert creds["host"] == "localhost"
    assert creds["database"] == "bravo_db"


def test_missing_profile_raises():
    with pytest.raises(RuntimeError):
        load_config("charlie")
