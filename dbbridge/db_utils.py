import logging
import re
import sys
from typing import Optional

import pymysql
import pymysql.cursors
from colorfulPyPrint.py_color import print_warning, input_white, print_error, print_blue, print_cyan
from string_list import string_from_list

import config

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger()

DB_CREDS = config.load_config()


# -- RUN SQL QUERY -- #
def run_sql(sql, as_dict: bool = True, quiet: Optional[bool] = None, db_creds: Optional[dict] = None):
    """
    The run_sql function is a wrapper for the pymysql library. It allows you to run SQL queries against your database
    without having to worry about connecting, disconnecting, or committing changes. The function takes in an SQL query
    as a string and executes it.
    Any results (for SELECT queries) are returned as a list of dictionaries or raw tuples if as_dict=False.
    You can also pass in your own db_creds dictionary with host, passwd, user, database

    :param sql: Pass the sql query to be executed
    :param as_dict: bool: Determine if the results are returned as a list of dictionaries or tuples
    :param quiet: Optional[bool]: Suppress output to the console
    :param db_creds: Optional[dict]: Allow the function to be used with different dbs
    :return: A list of dictionaries (if as_dict=true) or raw tuples (if as_dict=False)
    """
    # pick up default creds if none provided
    if db_creds is None:
        db_creds = config.load_config()

    sql = none_to_null(sql.strip())  # Replace any 'None'/None values with NULL

    # If CREATE/DROP do not run
    if re.search('^CREATE', sql, re.IGNORECASE) or re.search('^DROP', sql, re.IGNORECASE):
        raise Exception(f"SQL PERMISSION ERROR: {sql}\nCan not run CREATE/DROP query")
    # If UPDATE/DELETE do not run unless WHERE clause is present
    if re.search('^UPDATE', sql, re.IGNORECASE) or re.search('^DELETE FROM', sql, re.IGNORECASE):
        if not re.search('WHERE', sql, re.IGNORECASE):
            raise Exception(f"SQL ERROR: {sql}\nCan not run UPDATE/DELETE query without WHERE clause")

    # Connect to DB
    try:
        db = pymysql.connect(
            host=db_creds["host"],
            port=db_creds.get("port", 3306),
            user=db_creds["user"],
            password=db_creds["password"],
            database=db_creds["database"]
        )
    except Exception as e:
        logger.error(e)
        raise e

    # If connection established, create cursor
    if as_dict:
        cursor = db.cursor(cursor=pymysql.cursors.DictCursor)
    else:
        cursor = db.cursor()

    # Set quiet based on query type if quiet is not explicitly defined
    if quiet is None:
        if re.search(r'^(UPDATE |DELETE FROM |INSERT )', sql, re.IGNORECASE):
            quiet = False
        else:
            quiet = True
    try:
        if not quiet:
            print_cyan(f"Running query: \n{sql}")
        logger.info("Running query: %s" % sql)
        cursor.execute(sql)

        if re.search('^SELECT', sql, re.IGNORECASE):  # SELECT query
            if cursor.rowcount == 0:
                return []
            else:
                rows = cursor.fetchall()
                return rows
        elif re.search('^INSERT', sql, re.IGNORECASE):  # INSERT query
            db.commit()
            if quiet is False:
                print_cyan(f"{cursor.rowcount} rows were affected.", bold=True)
            logger.info(f"{cursor.rowcount} rows were affected.")
            return cursor.lastrowid
        elif re.search(r'^(UPDATE |DELETE FROM )', sql, re.IGNORECASE):  # UPDATE/DELETE FROM query
            db.commit()
            print_cyan("{} rows were affected.".format(cursor.rowcount), bold=True)
            logger.info(f"{cursor.rowcount} rows were affected.")
        else:
            raise ValueError(f"Unknown query type in {sql}")
    except Exception as e:
        logger.error(e)
        raise e
    finally:
        cursor.close()
        db.close()
        # print(rows)


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
