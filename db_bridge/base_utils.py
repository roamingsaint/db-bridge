# db_bridge/base_utils.py

from typing import List, Any, Optional, Union, Tuple

try:
    from colorfulPyPrint.py_color import print_exception
except ImportError:
    def print_exception(e):
        pass


class BaseBridge:
    """
    Base class for database bridges. Handles common run_sql, commit, and fetch logic.
    """
    def __init__(self, creds: dict, as_dict: bool = False) -> None:
        self.creds = creds
        self.as_dict = as_dict
        self.conn = None
        self.cursor = None

    def _prepare_sql(self, sql: str, params: list) -> Tuple[str, List[Any]]:
        """
        Driver-specific SQL preprocessing (e.g. placeholder translation).
        Override in subclasses if needed.
        """
        return sql, params

    def run_sql(
            self,
            sql: str,
            params: Optional[List[Any]] = None
    ) -> Union[List[dict], List[tuple]]:
        """
        Execute a SQL statement using the underlying cursor, with optional parameters.

        This method:
          1) Lets the subclass preprocess the SQL and params (e.g. placeholder translation).
          2) Executes the query.
          3) Fetches results as a list of rows (dicts if `as_dict=True`, otherwise tuples).
          4) Commits the transaction.

        Args:
            sql:    The SQL string to execute (may include ? or %s placeholders).
            params: Optional list of parameters to bind to the query.

        Returns:
            A list of rows, each row as a dict (if `self.as_dict`) or tuple.
        """
        # 1) SQL preprocessing
        sql, params = self._prepare_sql(sql, params or [])

        # 2) Execute
        self.cursor.execute(sql, params)

        # 3) Fetch
        if self.as_dict and getattr(self.cursor, "description", None):
            cols = [col[0] for col in self.cursor.description]
            rows = [dict(zip(cols, row)) for row in self.cursor.fetchall()]
        else:
            rows = self.cursor.fetchall()

        # 4) Commit and return
        self.conn.commit()
        return rows

    def get_last_row_id(self):
        return getattr(self.cursor, "lastrowid", None)

    def get_row_count(self):
        return getattr(self.cursor, "rowcount", None)

    def close(self):
        try:
            self.cursor.close()
            self.conn.close()
        except Exception as e:
            print_exception(e)
            pass
