import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    DATABASE_MODE = os.getenv("DATABASE_MODE", "sqlite").lower()

    if DATABASE_MODE == "sqlserver":
        SQLSERVER_DRIVER = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")
        SQLSERVER_SERVER = os.getenv("SQLSERVER_SERVER", "")
        SQLSERVER_DATABASE = os.getenv("SQLSERVER_DATABASE", "")
        SQLSERVER_USER = os.getenv("SQLSERVER_USER", "")
        SQLSERVER_PASSWORD = os.getenv("SQLSERVER_PASSWORD", "")

        connection_string = (
            f"DRIVER={{{SQLSERVER_DRIVER}}};"
            f"SERVER={SQLSERVER_SERVER};"
            f"DATABASE={SQLSERVER_DATABASE};"
            f"UID={SQLSERVER_USER};"
            f"PWD={SQLSERVER_PASSWORD};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=yes;"
            f"Connection Timeout=10;"
        )

        SQLALCHEMY_DATABASE_URI = (
            "mssql+pyodbc:///?odbc_connect="
            + quote_plus(connection_string)
        )

        AUTO_CREATE_TABLES = False
        DATABASE_LABEL = f"SQL Server: {SQLSERVER_SERVER} / {SQLSERVER_DATABASE}"

    else:
        SQLALCHEMY_DATABASE_URI = os.getenv(
            "DATABASE_URL",
            "sqlite:///wareneingang.db"
        )

        AUTO_CREATE_TABLES = True
        DATABASE_LABEL = "SQLite lokal"

    SQLALCHEMY_TRACK_MODIFICATIONS = False