import logging
import re
import sys
from typing import Optional, Tuple, Any, List, Union

import pymysql
import pymysql.cursors
from askuser import choose_from_db
from colorfulPyPrint.py_color import print_cyan

from . import config

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)


def replace_none_w_null(sql_text: str) -> str:
    """
    Replaces 'None' or "None" or None literals in SQL strings with SQL NULL.
    """
    replacements = [
        (r"'None'", "NULL"),
        (r'"None"', "NULL"),
        (r"None", "NULL"),
    ]
    for old, new in replacements:
        sql_text = re.sub(old, new, sql_text)
    return sql_text.strip()


def run_sql(sql: str, params: Optional[Tuple[Any, ...]] = None,
            as_dict: bool = True, quiet: Optional[bool] = None, none_to_null: bool = True,
            db_creds: Optional[dict] = None
            ) -> Union[List[dict], int]:
    """
    Execute an SQL statement with optional parameterization.
    If params is provided, runs a parameterized query; otherwise runs raw SQL.

    Args:
        sql: A native SQL query string, optionally using %s placeholders.
        params: Tuple of parameters to bind to the query (safe path).
        as_dict: Return rows as list of dicts (True) or tuples (False) for SELECT.
        quiet: If False, prints queries and row counts. Auto-determined if None.
        db_creds: Override credentials dict (host, port, user, password, database).
        none_to_null: On raw SQL mode (params=None), replace 'None' literals with NULL.

    Returns:
        SELECT -> List[dict] or List[tuple]
        INSERT -> int (last row id)
        UPDATE/DELETE -> int (affected rows count)
        Other -> []
    Raises:
        Exception: on connection errors, permission violations, or SQL execution errors.
    """

    # 1) Lazy-load credentials
    creds = db_creds if db_creds is not None else config.load_config()

    # 2) Prepare raw SQL
    raw_sql = sql.strip()
    if params is None and none_to_null:
        raw_sql = replace_none_w_null(raw_sql)

    # 3) Permission guards
    if re.match(r'^(CREATE|DROP)', raw_sql, re.IGNORECASE):
        raise Exception(f"SQL PERMISSION ERROR: {raw_sql}\nCREATE/DROP not allowed")
    if re.match(r'^(UPDATE|DELETE)', raw_sql, re.IGNORECASE) and not re.search(r'WHERE', raw_sql, re.IGNORECASE):
        raise Exception(f"SQL ERROR: {raw_sql}\nUPDATE/DELETE requires WHERE clause")

    # 4) Connect (pass **creds so tests can monkeypatch load_config → {} )
    try:
        cursor_cls = pymysql.cursors.DictCursor if as_dict else pymysql.cursors.Cursor
        conn = pymysql.connect(cursorclass=cursor_cls, **creds)
    except Exception as e:
        logger.error("DB connection failed", exc_info=e)
        raise

    cursor = conn.cursor()

    # 5) Determine default for quiet
    if quiet is None:
        quiet = False if re.match(r'^(UPDATE|DELETE|INSERT)', raw_sql, re.IGNORECASE) else True

    try:
        if not quiet:
            print_cyan(f"Running query:\n{raw_sql}")
        logger.info("Executing SQL: %s", raw_sql)

        # 6) Execute
        if params is not None:
            cursor.execute(raw_sql, params)
        else:
            cursor.execute(raw_sql)

        # 7) Handle results
        cmd = raw_sql.split()[0].upper()
        if cmd == "SELECT":
            rows = cursor.fetchall()
            return rows or []
        elif cmd == "INSERT":
            conn.commit()
            if not quiet:
                print_cyan(f"{cursor.rowcount} rows affected.", bold=True)
            logger.info("%d rows affected.", cursor.rowcount)
            return cursor.lastrowid
        elif cmd in ("UPDATE", "DELETE"):
            conn.commit()
            if not quiet:
                print_cyan(f"{cursor.rowcount} rows affected.", bold=True)
            logger.info("%d rows affected.", cursor.rowcount)
            return cursor.rowcount
        else:
            # Other commands (e.g., DDL)
            conn.commit()
            return []
    except Exception as e:
        logger.error("SQL execution failed", exc_info=e)
        raise
    finally:
        cursor.close()
        conn.close()


def get_column_values(*columns_to_return: str, table_name: str, unique_column_name: str, unique_column_value: Any,
                      primary_key: str = 'id', as_tuple: bool = True) -> Union[None, Tuple, dict]:
    """
    Retrieve specified column values from a database table based on a unique column value.

    This function fetches values for the specified columns (`columns_to_return`) in the specified `table_name`
    where a unique column (`unique_column_name`) matches a provided value (`unique_column_value`). If multiple
    rows match, the user is prompted to select one.

    Args:
        columns_to_return (str): Column names to retrieve values from.
        table_name (str): The name of the table to query.
        unique_column_name (str): The name of the unique column to filter by.
        unique_column_value (str/int): The exact value to match in `unique_column_name`.
        primary_key (str): Default: 'id'. Primary_key of the table. Helps choose if there are multiple values.
        as_tuple (bool): If True, returns the result as a tuple in the order of `columns_to_return`;
                         if False, returns as a dictionary.

    Returns:
      - None if no matches
      - A tuple of values (in order of columns_to_return) if as_tuple=True
      - A dict of {column: value} if as_tuple=False

    Raises:
        Exception: If an error occurs during SQL execution.
    """
    # Build a parameterized SQL string
    cols = ",".join(columns_to_return)
    # ensure primary_key is selected if needed
    select_cols = (
        f"{primary_key}, {cols}"
        if primary_key not in columns_to_return
        else cols
    )
    sql = f"SELECT {select_cols} FROM {table_name} WHERE {unique_column_name} = %s"
    # Run with parameter binding for safety
    rows: List[dict] = run_sql(sql, params=(unique_column_value,), as_dict=True)

    if not rows:
        return None

    if len(rows) > 1:
        chosen_id, chosen_row = choose_from_db(
            rows,
            input_msg=f"Select the correct {table_name} {primary_key}",
            primary_key=primary_key,
            table_desc=f"{table_name} matches for {unique_column_value}",
            xq=False
        )
        row = chosen_row
    else:
        row = rows[0]  # Single match found, no user input required

    # If caller wants a tuple
    if as_tuple:
        if len(columns_to_return) == 1:
            return row[columns_to_return[0]]
        return tuple(row[col] for col in columns_to_return)

    # as_dict: drop the primary_key if it was not requested
    if primary_key not in columns_to_return:
        row.pop(primary_key, None)
    return row


def get_column_values_regexp(*columns_to_return: str, table_name: str,
                             unique_column_name: str, unique_column_regexp: str
                             ) -> List[dict]:
    """
    Returns column values based on tbl_name, unique_column_name and a REGEXP for unique_column_name's value
     - ** NOTE: WILL return multiple values **

    Args:
        columns_to_return: Columns to select.
        table_name: Table name.
        unique_column_name: Column against which to apply the REGEXP.
        unique_column_regexp: The REGEXP pattern to match.

    Returns:
        List[dict]: One dict per matching row. [] list if no matches.
    """
    # Build a parameterized query to avoid injection
    cols = ",".join(columns_to_return)
    sql = f"SELECT {cols} FROM {table_name} WHERE {unique_column_name} REGEXP %s"

    # Use run_sql with params; always returns list of dicts
    rows = run_sql(sql, params=(unique_column_regexp,), as_dict=True)

    return rows  # Returns [] if no matches found
