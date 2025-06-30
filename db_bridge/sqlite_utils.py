# db_bridge/sqlite_utils.py

import sqlite3
from pathlib import Path
from typing import Tuple, List, Any

from .base_utils import BaseBridge


class SQLiteBridge(BaseBridge):
    """
    SQLite adapter for db-bridge, using the built-in sqlite3 module.
    """

    def __init__(self, creds: dict, as_dict: bool = False) -> None:
        """
        Initialize an SQLite connection, creating parent directories if needed.

        Args:
            creds:   Dict with at least 'database' (path to .db file), plus 'driver'.
            as_dict: If True, returns each row as a dict; otherwise as tuple.
        """
        super().__init__(creds, as_dict)

        db_path = creds["database"]
        # Ensure the directory exists so sqlite can create the file
        parent = Path(db_path).parent
        parent.mkdir(parents=True, exist_ok=True)
        # Open (and create) the SQLite file
        self.conn = sqlite3.connect(db_path)

        # If the user wants dicts, set row_factory
        if as_dict:
            self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def _prepare_sql(self, sql: str, params: list) -> Tuple[str, List[Any]]:
        """
        Translate MySQL-style %s placeholders into sqlite3 '?' placeholders.
        """
        return sql.replace("%s", "?"), params
