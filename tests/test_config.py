import pytest

from dbbridge import config


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    for var in ("DB_NAME", "DB_USER", "DB_PASS", "DB_HOST", "DB_PORT", "DBBRIDGE_PROFILE"):
        monkeypatch.delenv(var, raising=False)


def test_env_override(monkeypatch):
    monkeypatch.setenv("DB_NAME", "db1")
    monkeypatch.setenv("DB_USER", "user1")
    monkeypatch.setenv("DB_PASS", "pw1")
    monkeypatch.setenv("DB_HOST", "h1")
    monkeypatch.setenv("DB_PORT", "1234")

    cfg = config.load_config()
    assert cfg["database"] == "db1"
    assert cfg["user"] == "user1"
    assert cfg["password"] == "pw1"
    assert cfg["host"] == "h1"
    assert cfg["port"] == 1234


def test_ini_fallback(tmp_path, monkeypatch):
    # Create ~/.dbbridge.cfg in a temp home
    ini = tmp_path / ".dbbridge.cfg"
    ini.write_text(
        "[DEFAULT]\n"
        "active = prof1\n"
        "[prof1]\n"
        "host = localhost\n"
        "port = 3307\n"
        "name = db2\n"
        "user = user2\n"
        "password = pw2\n"
    )
    monkeypatch.setenv("HOME", str(tmp_path))

    cfg = config.load_config()
    assert cfg["database"] == "db2"
    assert cfg["user"] == "user2"
    assert cfg["password"] == "pw2"
    assert cfg["host"] == "localhost"
    assert cfg["port"] == 3307
