# db_bridge/mysql_utils.py

import pymysql
import pymysql.cursors

from .base_utils import BaseBridge


class MySQLBridge(BaseBridge):
    """
    MySQL adapter for db-bridge, using PyMySQL under the hood.

    Expects creds dict keys:
        - host, port, user, password, database
    """

    def __init__(self, creds: dict, as_dict: bool = False) -> None:
        """
        Initialize a MySQL connection.

        Args:
            creds:   Dict with connection parameters:
                     host, port, user, password, database, (driver ignored).
            as_dict: If True, returns each row as a dict; otherwise as tuple.
        """
        super().__init__(creds, as_dict)
        # Choose the cursor class
        cursor_cls = pymysql.cursors.DictCursor if as_dict else pymysql.cursors.Cursor
        # Establish the connection
        conn_args = {k: v for k, v in creds.items() if k != "driver"}
        self.conn = pymysql.connect(cursorclass=cursor_cls, **conn_args)
        # Create a cursor for executing queries
        self.cursor = self.conn.cursor()
