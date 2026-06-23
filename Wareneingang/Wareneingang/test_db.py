from app.db import fetch_all, is_database_configured, test_connection


def print_rows(title, rows):
    print(title)

    if not rows:
        print("  keine Treffer")
        return

    for row in rows:
        print(f"  {row}")


if not is_database_configured():
    print("Datenbank ist nicht vollstaendig konfiguriert.")
    print("Bitte .env mit DB_SERVER, DB_NAME und Login-Daten pruefen.")
    raise SystemExit(1)

try:
    test_connection()
    print("Datenbankverbindung OK")

    views = fetch_all("""
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME
        FROM INFORMATION_SCHEMA.VIEWS
        WHERE TABLE_SCHEMA IN ('list_views', 'ins_views', 'upd_views', 'lov_views')
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    """)
    print_rows("Gefundene Views:", views)

    routines = fetch_all("""
        SELECT
            ROUTINE_SCHEMA,
            ROUTINE_NAME,
            ROUTINE_TYPE
        FROM INFORMATION_SCHEMA.ROUTINES
        WHERE ROUTINE_SCHEMA = 'stored_func'
        ORDER BY ROUTINE_SCHEMA, ROUTINE_NAME
    """)
    print_rows("Gefundene Stored Functions:", routines)

except Exception as exc:
    print("Fehler beim Datenbankcheck:")
    print(exc)
    raise
