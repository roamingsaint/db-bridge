# db_bridge/db_utils.py

import logging
import re
import sys
from typing import Optional, Tuple, Any, List, Union, Dict

from askuser import choose_from_db

from .mysql_utils import MySQLBridge
from .postgres_utils import PostgresBridge
from .sqlite_utils import SQLiteBridge

# Attempt to import print_custom; if missing, define a no-op
try:
    from colorfulPyPrint.py_color import print_custom, print_error

    COLOR_PRINT = True
except ImportError:
    COLOR_PRINT = False

    def print_custom(msg, *args, **kwargs):
        print(msg)

    def print_error(msg):
        print(f"❌{msg}")

from . import config

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)


class DBBridgeError(Exception):
    """Base exception for db-bridge errors."""


class SQLPermissionError(DBBridgeError):
    """Raised when a disallowed SQL command is attempted."""


class SQLExecutionError(DBBridgeError):
    """Raised when SQL execution fails (wraps the original error)."""


class NoRowFoundError(DBBridgeError):
    """Raised when get_column_values finds no matching rows."""


def _info_message(msg: str, *, color_msg: Optional[str] = None, color='cyan'):
    """
    Show an informational message. If colorfulPyPrint is installed,
    use print_custom(color_msg); otherwise, use logger.info(msg).
    color_msg may be different (e.g. no ANSI codes) from msg.
    Check colorfulPyPrint.py_color.print_custom for allowed color options
    """
    if COLOR_PRINT and color_msg is not None:
        print_custom(f"<{color}:{color_msg}>")
    else:
        logger.info(msg)


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


def run_sql(
        sql: str,
        params: Optional[Tuple[Any, ...]] = None,
        *,
        as_dict: bool = True,
        quiet: Optional[bool] = None,
        none_to_null: bool = True,
        db_bridge_profile: str = None,
        db_creds: Optional[dict] = None
) -> Union[List[dict], int]:
    """
    Execute an SQL statement with optional parameterization against a chosen DB profile.

    Args:
        sql:          SQL query string (use %s placeholders in all drivers).
        params:       Parameters tuple for safe parameterized queries.
        as_dict:      Return rows as dicts (True) or tuples (False).
        quiet:        Suppress SQL and row-count output if True.
        none_to_null: Replace literal None in raw SQL with SQL NULL.
        db_bridge_profile: INI section name to use (falls back to [DEFAULT].active).
        db_creds:     Direct credentials dict; mutually exclusive with profile.

    Returns:
        List of rows (dict or tuple) for SELECT; rowcount/lastrowid for writes.

    Raises:
        ValueError: If both `profile` and `db_creds` are given.
        Exception: On SQL permission errors or execution failures.
    """

    # 1) Credentials: either db_creds or an INI profile (never both)
    if db_creds and db_bridge_profile:
        raise ValueError("Specify only one of db_creds or profile, not both.")
    creds = db_creds if db_creds else config.load_config(db_bridge_profile)
    driver = creds.get("driver", "mysql").lower()

    # 2) Prepare raw SQL
    raw_sql = sql.strip()
    if params is None and none_to_null:
        raw_sql = replace_none_w_null(raw_sql)

    # 3) Permission guards (Not allowed: CREATE/DROP, UPDATE/DELETE without WHERE)
    if driver != "sqlite" and re.match(r'^(CREATE|DROP)', raw_sql, re.IGNORECASE):
        raise SQLPermissionError(f"Disallowed DDL on non-SQLite driver: {raw_sql}")
    if re.match(r'^(UPDATE|DELETE)', raw_sql, re.IGNORECASE) and not re.search(r'WHERE', raw_sql, re.IGNORECASE):
        raise SQLPermissionError(f"UPDATE/DELETE requires WHERE clause: {raw_sql}")

    # 4) Connect via adapter
    if driver == "sqlite":
        bridge = SQLiteBridge(creds, as_dict=as_dict)
    elif driver == "mysql":
        bridge = MySQLBridge(creds, as_dict=as_dict)
    elif driver == "postgres":
        bridge = PostgresBridge(creds, as_dict=as_dict)
    else:
        raise ValueError(f"Unsupported driver: {driver}")
    cursor = bridge.cursor
    conn = bridge.conn

    # 5) Build final SQL for logging, if possible
    final_sql = raw_sql
    if params is not None:
        # Only attempt mogrify if the cursor actually supports it
        if hasattr(cursor, "mogrify"):
            try:
                mogrified = cursor.mogrify(raw_sql, params)
                # PyMySQL’s mogrify returns bytes, so decode if needed
                final_sql = mogrified.decode() if isinstance(mogrified, bytes) else mogrified
            except (AttributeError, TypeError, ValueError) as e:
                logger.warning(
                    "Could not mogrify SQL with params %r: %s. Falling back to raw SQL.",
                    params,
                    e,
                )
                final_sql = raw_sql + f"  -- params: {params!r}"
        else:
            # Cursor has no mogrify (unlikely with PyMySQL, but just in case)
            final_sql = raw_sql + f"  -- params: {params!r}"
    # else: params is None → caller passed full SQL; final_sql stays as raw_sql

    # 6) Determine default for quiet
    if quiet is None:
        quiet = False if re.match(r'^(UPDATE|DELETE|INSERT)', raw_sql, re.IGNORECASE) else True

    try:
        # 7) Show or log the SQL before executing
        if not quiet:
            _info_message(final_sql, color_msg=final_sql, color="cyan")

        # 8) Execute (swap %s→? for SQLite if params given)
        exec_sql = raw_sql.replace("%s", "?") if (driver == "sqlite" and params) else raw_sql

        if params is not None:
            cursor.execute(exec_sql, params)
        else:
            cursor.execute(exec_sql)

        # 9) Decide result behavior:
        # If the statement produced a result set, cursor.description will be non-None.
        if cursor.description is not None:
            rows = cursor.fetchall() or []
            return rows

        # Otherwise, it's a write/DDL/etc.; commit and choose a sensible return value.
        # We still try to detect INSERT/UPDATE/DELETE for nicer return semantics.
        match = re.search(r'^\s*(?:--.*\n\s*)*([A-Za-z]+)', raw_sql)
        cmd = match.group(1).upper() if match else ''

        conn.commit()

        if cmd == "INSERT":
            affected = cursor.rowcount
            if not quiet:
                _info_message(f"{affected} rows affected.", color_msg=f"{affected} rows affected.", color="bold_cyan")
            return cursor.lastrowid

        if cmd in ("UPDATE", "DELETE"):
            affected = cursor.rowcount
            if not quiet:
                _info_message(f"{affected} rows affected.", color_msg=f"{affected} rows affected.", color="bold_cyan")
            return affected

        # DDL or other statements → no result set; return empty list for consistency.
        return []
    except Exception as e:
        logger.error("SQL execution failed for: %s", final_sql, exc_info=e)
        print_error(f"SQL query: {final_sql}")
        raise SQLExecutionError(f"Failed to execute SQL: {e}") from e
    finally:
        bridge.close()


def get_column_values(
        *columns_to_return: str,
        table_name: str,
        unique_column_name: str,
        unique_column_value: Any,
        primary_key: str = 'id',
        as_tuple: bool = True,
        error_if_missing: bool = True,
        db_bridge_profile: str = None,
        db_creds: Optional[dict] = None
) -> Optional[Union[Tuple[Any, ...], Dict[str, Any]]]:
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
        primary_key (str): Default: 'id'. Primary key of the table (used to disambiguate multiples).
        as_tuple (bool): If True, returns the result as a tuple in the order of `columns_to_return`;
                         if False, returns as a dictionary.
        error_if_missing (bool): If True (default), raises NoRowFoundError when there are no matches.
                       If False, returns None when there are no matches.
        db_bridge_profile: INI section name to use (falls back to [DEFAULT].active).
        db_creds:     Direct credentials dict; mutually exclusive with profile.

    Returns:
        - None if no matches and error_if_missing=False
        - A tuple of values (in order of columns_to_return) if as_tuple=True
        - A dict of {column: value} if as_tuple=False

    Raises:
        NoRowFoundError: If no rows match and error_if_missing=True.
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
    rows: List[dict] = run_sql(sql, params=(unique_column_value,), as_dict=True,
                               db_bridge_profile=db_bridge_profile, db_creds=db_creds)

    if not rows:
        if error_if_missing:
            raise NoRowFoundError(f"No rows found in {table_name} where {unique_column_name} = {unique_column_value!r}")
        return None

    if len(rows) > 1:
        chosen_id, chosen_row = choose_from_db(
            rows,
            input_msg=f"Select the correct {table_name} {primary_key}",
            primary_key=primary_key,
            table_desc=f"{table_name} matches for {unique_column_value}",
            xq=False,
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


def get_column_values_regexp(
        *columns_to_return: str,
        table_name: str,
        unique_column_name: str,
        unique_column_regexp: str,
        db_bridge_profile: str = None,
        db_creds: Optional[dict] = None
) -> List[dict]:
    """
    Returns column values based on tbl_name, unique_column_name and a REGEXP for unique_column_name's value
     - ** NOTE: WILL return multiple values **

    Args:
        columns_to_return: Columns to select.
        table_name: Table name.
        unique_column_name: Column against which to apply the REGEXP.
        unique_column_regexp: The REGEXP pattern to match.
        db_bridge_profile: INI section name to use (falls back to [DEFAULT].active).
        db_creds:     Direct credentials dict; mutually exclusive with profile.

    Returns:
        List[dict]: One dict per matching row. [] list if no matches.
    """
    cols = ",".join(columns_to_return)
    sql = f"SELECT {cols} FROM {table_name} WHERE {unique_column_name} REGEXP %s"
    rows = run_sql(sql, params=(unique_column_regexp,), as_dict=True,
                   db_bridge_profile=db_bridge_profile, db_creds=db_creds)
    return rows  # Returns [] if no matches found
