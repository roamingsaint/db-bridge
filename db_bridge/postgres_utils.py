# db_bridge/postgres_utils.py

import psycopg2
import psycopg2.extras
from .base_utils import BaseBridge


class PostgresBridge(BaseBridge):
    """
    PostgreSQL adapter for db-bridge, using psycopg2 under the hood.
    """

    def __init__(self, creds: dict, as_dict: bool = False) -> None:
        """
        Args:
            creds:   Dict with keys host, port, user, password, database.
            as_dict: If True, returns rows as dicts; otherwise tuples.
        """
        super().__init__(creds, as_dict)
        # Choose cursor factory
        cursor_factory = psycopg2.extras.DictCursor if as_dict else None
        # Establish connection
        conn_args = {
            "host": creds["host"],
            "port": creds["port"],
            "user": creds["user"],
            "password": creds["password"],
            "dbname": creds["database"],
            "cursor_factory": cursor_factory
        }
        self.conn = psycopg2.connect(**conn_args)
        self.cursor = self.conn.cursor()

    # No placeholder translation needed—psycopg2 also uses %s
