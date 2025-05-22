import logging
import re
import sys
from typing import Optional, Tuple, Any, List

import pymysql
import pymysql.cursors
from colorfulPyPrint.py_color import print_warning, input_white, print_error, print_blue, print_cyan
from askuser import choose_from_db

import config

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

# Load default database credentials at import time
DB_CREDS = config.load_config()


def _none_to_null(sql_text: str) -> str:
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
            as_dict: bool = True, quiet: Optional[bool] = None,
            none_to_null: bool = True, db_creds: Optional[dict] = None,
            ) -> Any:
    """
    Execute an SQL statement with optional parameterization.

    - If `params` is provided, executes a parameterized query:
        cursor.execute(sql, params)
      ensuring proper escaping and injection safety.

    - If `params` is None, executes raw SQL:
        cursor.execute(sql)
      optionally cleaning 'None'→NULL in the SQL string if `none_to_null` is True.

    Permission checks (CREATE/DROP, UPDATE/DELETE without WHERE) are applied
    on the raw SQL text.

    Args:
        sql: A native SQL query string, optionally using %s placeholders.
        params: Tuple of parameters to bind to the query (safe path).
        as_dict: Return rows as list of dicts (True) or tuples (False) for SELECT.
        quiet: If False, prints queries and row counts. Auto-determined if None.
        db_creds: Override credentials dict (host, port, user, password, database).
        none_to_null: On raw SQL mode (params=None), replace 'None' literals with NULL.

    Returns:
        SELECT -> List[dict] or List[tuple],
        INSERT -> int (last row id),
        UPDATE/DELETE -> int (affected rows count),
        Other -> [].

    Raises:
        Exception: on connection errors, permission violations, or SQL execution errors.
    """
    # Load credentials
    creds = db_creds or DB_CREDS

    # Prepare SQL
    raw_sql = sql.strip()
    if params is None and none_to_null:
        raw_sql = _none_to_null(raw_sql)

    # Permission guards
    # If CREATE/DROP do not run
    if re.match(r'^(CREATE|DROP)', raw_sql, re.IGNORECASE):
        raise Exception(f"SQL PERMISSION ERROR: {raw_sql}\nCREATE/DROP not allowed")
    # If UPDATE/DELETE do not run unless WHERE clause is present
    if re.match(r'^(UPDATE|DELETE)', raw_sql, re.IGNORECASE) and not re.search(r'WHERE', raw_sql, re.IGNORECASE):
        raise Exception(f"SQL ERROR: {raw_sql}\nUPDATE/DELETE requires WHERE clause")

    # Connect
    try:
        conn = pymysql.connect(
            host=creds["host"],
            port=creds.get("port", 3306),
            user=creds["user"],
            password=creds["password"],
            database=creds["database"],
            cursorclass=(pymysql.cursors.DictCursor if as_dict else pymysql.cursors.Cursor)
        )
    except Exception as e:
        logger.error("DB connection failed", exc_info=e)
        raise

    cursor = conn.cursor()

    # Determine quiet default
    if quiet is None:
        if re.match(r'^(UPDATE|DELETE|INSERT)', raw_sql, re.IGNORECASE):
            quiet = False
        else:
            quiet = True

    try:
        if not quiet:
            print_cyan(f"Running query:\n{raw_sql}")
        logger.info("Executing SQL: %s", raw_sql)

        # Execute
        if params is not None:
            cursor.execute(raw_sql, params)
        else:
            cursor.execute(raw_sql)

        # Process result
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


def get_column_values(*columns_to_return, table_name, unique_column_name, unique_column_value, as_tuple=True):
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
        as_tuple (bool): If True, returns the result as a tuple in the order of `columns_to_return`;
                         if False, returns as a dictionary.

    Returns:
        dict or tuple: Returns either a dictionary or tuple of column values for the matching row.
                       Returns None if no matches are found.

    Raises:
        Exception: If an error occurs during SQL execution.
    """
    try:
        # Build SQL query
        sql = "SELECT "
        sql += "id, " if "id" not in columns_to_return else ""  # 'id' tp help if multiple results. Is dropped later.
        sql += f"{','.join(columns_to_return)} FROM {table_name} WHERE {unique_column_name}='{unique_column_value}'"

        # Execute SQL query
        result = run_sql(sql)
    except Exception as e:
        raise Exception(f"SQL Execution Error: {e}")

    # Handle query results based on number of matching rows
    if len(result) == 0:
        return None  # No results found
    elif len(result) > 1:
        print_warning("Multiple results found!")

        # Create options for user to select correct record by 'id'
        choices = {f"{s['id']}": s for s in result}
        readable_choices = {f"{s['id']}": string_from_list([f'{k}: {v}' for k, v in s.items()], delim=' | ') for s in
                            result}

        # Display available choices to the user
        for k, v in readable_choices.items():
            print_blue(f'{k}: ', end='')
            print(f'{v}')

        # Prompt user to select an id
        while True:
            opt_id = input_white("Choose the correct id: ")
            if opt_id not in readable_choices.keys():
                print_error(f"Only choices allowed are {list(readable_choices.keys())}")
            else:
                break

        return_val = choices[opt_id]
    else:
        return_val = result[0]  # Single match found, no user input required

    # Return the result as either a tuple or a dictionary
    if as_tuple:
        # For a single column, return a scalar; for multiple columns, return a tuple
        return return_val[columns_to_return[0]] if len(columns_to_return) == 1 \
            else tuple([return_val[col] for col in columns_to_return])
    else:
        # Remove 'id' if it was added for handling multiple results and not requested
        if "id" not in columns_to_return:
            return_val.pop('id')
        return return_val


def get_column_values_regexp(*columns_to_return, table_name, unique_column_name, unique_column_regexp):
    """
    Returns column values based on tbl_name, unique_column_name and a REGEXP for unique_column_name's value
     - ** NOTE: WILL return multiple values **
    Example:
    :param columns_to_return: list of columns whose value is returned
    :param table_name: table to lookup
    :param unique_column_name: name of unique_column in the table
    :param unique_column_regexp: REGEXP to match in unique_column_value
    :return: dict of all columns values that match the REGEXP for the unique_column
    """
    try:
        result = run_sql(f"SELECT {','.join(columns_to_return)} "
                         f"FROM {table_name} WHERE {unique_column_name} REGEXP '{unique_column_regexp}'")
    except Exception as e:
        raise Exception(e)

    if len(result) > 1:
        print_warning(f"Multiple ({len(result)}) results found!")
        return result
    elif len(result) == 0:
        return None
    else:
        return result
