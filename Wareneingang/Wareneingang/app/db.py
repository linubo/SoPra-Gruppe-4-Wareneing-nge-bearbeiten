import os
import re

from dotenv import load_dotenv


load_dotenv()


class DatabaseNotConfiguredError(RuntimeError):
    pass


def _env_flag(name, default=False):
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "ja", "on"}


def _query_params(params):
    if params is None:
        return []

    if isinstance(params, (list, tuple)):
        return list(params)

    return [params]


def is_database_configured():
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    trusted_connection = _env_flag("DB_TRUSTED_CONNECTION", default=False)

    return bool(server and database and (trusted_connection or (user and password)))


def get_database_settings():
    return {
        "server": os.getenv("DB_SERVER"),
        "database": os.getenv("DB_NAME"),
        "driver": os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server"),
        "trusted_connection": _env_flag("DB_TRUSTED_CONNECTION", default=False),
        "encrypt": _env_flag("DB_ENCRYPT", default=True),
        "trust_server_certificate": _env_flag(
            "DB_TRUST_SERVER_CERTIFICATE",
            default=True
        ),
    }


def build_connection_string():
    if not is_database_configured():
        raise DatabaseNotConfiguredError(
            "Datenbank ist nicht vollstaendig konfiguriert. "
            "Bitte DB_SERVER, DB_NAME und entweder DB_USER/DB_PASSWORD "
            "oder DB_TRUSTED_CONNECTION=yes in der .env setzen."
        )

    settings = get_database_settings()
    parts = [
        f"DRIVER={{{settings['driver']}}}",
        f"SERVER={settings['server']}",
        f"DATABASE={settings['database']}",
    ]

    if settings["trusted_connection"]:
        parts.append("Trusted_Connection=yes")
    else:
        parts.extend([
            f"UID={os.getenv('DB_USER')}",
            f"PWD={os.getenv('DB_PASSWORD')}",
        ])

    parts.append(f"Encrypt={'yes' if settings['encrypt'] else 'no'}")

    if settings["trust_server_certificate"]:
        parts.append("TrustServerCertificate=yes")

    return ";".join(parts) + ";"


def get_db_connection():
    try:
        import pyodbc

    except ImportError as exc:
        raise RuntimeError(
            "pyodbc ist nicht installiert. Bitte requirements.txt installieren "
            "und den passenden ODBC Driver fuer SQL Server einrichten."
        ) from exc

    return pyodbc.connect(build_connection_string())


def rows_to_dicts(cursor, rows):
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


def fetch_all(query, params=None):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, *_query_params(params))
        rows = cursor.fetchall()
        return rows_to_dicts(cursor, rows)

    finally:
        cursor.close()
        connection.close()


def fetch_one(query, params=None):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, *_query_params(params))
        row = cursor.fetchone()

        if row is None:
            return None

        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, row))

    finally:
        cursor.close()
        connection.close()


def execute_query(query, params=None):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, *_query_params(params))
        connection.commit()
        return True

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def execute_transaction(callback):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        result = callback(cursor)
        connection.commit()
        return result

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


_QUALIFIED_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$")


def call_scalar_function(function_name, params=None, cursor=None):
    if not _QUALIFIED_NAME_PATTERN.match(function_name):
        raise ValueError(f"Ungueltiger SQL-Funktionsname: {function_name}")

    params = _query_params(params)
    placeholders = ", ".join("?" for _ in params)
    query = f"SELECT {function_name}({placeholders}) AS RETVAL"

    if cursor is not None:
        cursor.execute(query, *params)
        row = cursor.fetchone()
    else:
        row = fetch_one(query, params)

    if row is None:
        return None

    if isinstance(row, dict):
        return row.get("RETVAL")

    return getattr(row, "RETVAL", None)


def test_connection():
    return fetch_one("SELECT 1 AS CONNECTION_OK")
