import pytest
import pymysql

from dbbridge import db_utils, config

class DummyCursor:
    def __init__(self, rows):
        self._rows = rows
    def execute(self, sql):
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
    # fake config
    monkeypatch.setattr(config, "load_config", lambda: {})
    # fake pymysql.connect
    dummy_rows = [{"a": 1}, {"a": 2}]
    dummy = DummyConn(DummyCursor(dummy_rows))
    monkeypatch.setattr(pymysql, "connect", lambda **kw: dummy)

    res = db_utils.run_sql("SELECT * FROM x")
    assert res == dummy_rows

def test_run_sql_commit(monkeypatch):
    monkeypatch.setattr(config, "load_config", lambda: {})
    dummy = DummyConn(DummyCursor([]))
    monkeypatch.setattr(pymysql, "connect", lambda **kw: dummy)

    # should not raise on non-select
    assert db_utils.run_sql("UPDATE x SET a=1") == []
