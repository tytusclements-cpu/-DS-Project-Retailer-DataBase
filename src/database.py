# database.py
# Handles the connection between the Python application and Oracle Database.

import os
from contextlib import contextmanager

import oracledb


# --------------------------------------------------
# DATABASE CONFIGURATION
# --------------------------------------------------
# Defaults can be overridden with environment variables so the same code can
# point at a development, test, or production database without editing files.

DB_USER = os.environ.get("RETAIL_DB_USER", "your_username")
DB_PASSWORD = os.environ.get("RETAIL_DB_PASSWORD", "your_password")
DB_HOST = os.environ.get("RETAIL_DB_HOST", "localhost")
DB_PORT = int(os.environ.get("RETAIL_DB_PORT", "1521"))
DB_SERVICE = os.environ.get("RETAIL_DB_SERVICE", "XEPDB1")

# Why the most recent execute_query() returned nothing (None = it worked).
# Lets the graphical interface tell "no rows" apart from "query failed".
last_query_error = None


# --------------------------------------------------
# CREATE DATABASE CONNECTION
# --------------------------------------------------

def get_connection():
    """
    Connects to the Oracle database.

    Returns:
        Oracle database connection if successful.
        None if the connection fails.
    """

    try:
        connection = oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
        )

        return connection

    except oracledb.Error as error:
        print("Database connection failed:", error)
        return None


# --------------------------------------------------
# EXECUTE SQL QUERY
# --------------------------------------------------

def execute_query(sql, parameters=None):
    """
    Executes a SELECT query and returns the results.

    Args:
        sql: SQL SELECT statement.
        parameters: Optional dictionary of query parameters.

    Returns:
        List of rows returned by the query.
    """

    global last_query_error

    last_query_error = None
    connection = get_connection()

    if connection is None:
        last_query_error = "Could not connect to the database."
        return []

    try:
        cursor = connection.cursor()

        cursor.execute(sql, parameters or {})

        results = cursor.fetchall()

        return results

    except oracledb.Error as error:
        last_query_error = str(error)
        print("Query execution failed:", error)
        return []

    finally:
        if 'cursor' in locals():
            cursor.close()

        connection.close()


# --------------------------------------------------
# INSERT, UPDATE, AND DELETE
# --------------------------------------------------

def execute_update(sql, parameters=None):
    """
    Executes INSERT, UPDATE, or DELETE statements.

    Automatically commits successful changes.

    Returns:
        True if successful.
        False if an error occurs.
    """

    connection = get_connection()

    if connection is None:
        return False

    try:
        cursor = connection.cursor()

        cursor.execute(sql, parameters or {})

        connection.commit()

        return True

    except oracledb.Error as error:
        connection.rollback()

        print("Database update failed:", error)

        return False

    finally:
        if 'cursor' in locals():
            cursor.close()

        connection.close()


# --------------------------------------------------
# TRANSACTION HELPER
# --------------------------------------------------

class DatabaseUnavailableError(Exception):
    """Raised when a connection to the database cannot be established."""


@contextmanager
def db_session():
    """
    Yields a cursor inside one transaction.

    Commits when the block finishes normally, rolls everything back if any
    exception escapes the block, and always closes the cursor and connection.
    Use this when several statements must succeed or fail together.

    Raises:
        DatabaseUnavailableError: if no connection could be made.
    """

    connection = get_connection()

    if connection is None:
        raise DatabaseUnavailableError(
            "Could not connect to the database. "
            "Check the RETAIL_DB_* settings in database.py."
        )

    cursor = connection.cursor()

    try:
        yield cursor
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


# --------------------------------------------------
# TEST DATABASE CONNECTION
# --------------------------------------------------

def test_connection():
    """
    Checks whether the application can connect to Oracle.
    """

    connection = get_connection()

    if connection is not None:

        try:
            cursor = connection.cursor()

            cursor.execute("SELECT SYSDATE FROM DUAL")

            result = cursor.fetchone()

            print("Oracle database date:", result[0])

            return True

        except oracledb.Error as error:
            print("Connection test failed:", error)
            return False

        finally:
            cursor.close()
            connection.close()

    return False


# --------------------------------------------------
# MAIN PROGRAM
# --------------------------------------------------

if __name__ == "__main__":

    print("Testing Retail Database Connection...")

    if test_connection():
        print("Database connection test successful!")
    else:
        print("Could not connect to the database.")