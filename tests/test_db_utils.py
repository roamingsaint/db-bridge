import pytest
import pymysql

from db_bridge.db_utils import run_sql
from db_bridge import config


class DummyCursor:
    def __init__(self, rows, rowcount=0, lastrowid=None):
        self._rows = rows
        self.rowcount = rowcount
        self.lastrowid = lastrowid

    def execute(self, sql, params=None):
        pass

    def fetchall(self):
        return self._rows

    def close(self):
        pass


class DummyConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def close(self):
        pass


def test_run_sql_select(monkeypatch):
    monkeypatch.setattr(config, "load_config", lambda: {})
    dummy_rows = [{"a": 1}, {"a": 2}]
    dummy = DummyConn(DummyCursor(dummy_rows))
    monkeypatch.setattr(pymysql, "connect", lambda **kw: dummy)

    res = run_sql("SELECT * FROM x", params=None)
    assert res == dummy_rows


def test_run_sql_insert(monkeypatch):
    monkeypatch.setattr(config, "load_config", lambda: {})
    dummy = DummyConn(DummyCursor([], rowcount=1, lastrowid=42))
    monkeypatch.setattr(pymysql, "connect", lambda **kw: dummy)

    res = run_sql("INSERT INTO x VALUES (1)", params=None)
    assert res == 42


def test_run_sql_update(monkeypatch):
    monkeypatch.setattr(config, "load_config", lambda: {})
    dummy = DummyConn(DummyCursor([], rowcount=3))
    monkeypatch.setattr(pymysql, "connect", lambda **kw: dummy)

    res = run_sql("UPDATE x SET a=1 WHERE id=2", params=None)
    assert res == 3
