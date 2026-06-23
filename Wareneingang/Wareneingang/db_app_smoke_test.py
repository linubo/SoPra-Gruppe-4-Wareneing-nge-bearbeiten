from app import create_app
from app.db import fetch_all, fetch_one, get_database_settings, test_connection
from app.routes.db_status_routes import REQUIRED_FUNCTIONS, REQUIRED_VIEWS


def _exists(query, params):
    return bool(fetch_all(query, params))


def _print_missing_objects():
    missing_views = []
    for schema, view_name in REQUIRED_VIEWS:
        exists = _exists(
            """
            SELECT 1 AS FOUND
            FROM INFORMATION_SCHEMA.VIEWS
            WHERE TABLE_SCHEMA = ?
              AND TABLE_NAME = ?
            """,
            [schema, view_name],
        )
        if not exists:
            missing_views.append(f"{schema}.{view_name}")

    missing_functions = []
    for function in REQUIRED_FUNCTIONS:
        placeholders = ", ".join("?" for _ in function["names"])
        exists = _exists(
            f"""
            SELECT 1 AS FOUND
            FROM INFORMATION_SCHEMA.ROUTINES
            WHERE ROUTINE_SCHEMA = ?
              AND ROUTINE_NAME IN ({placeholders})
            """,
            [function["schema"], *function["names"]],
        )
        if not exists:
            missing_functions.append(function["display_name"])

    print("Required views missing:", missing_views or "none")
    print("Required functions missing:", missing_functions or "none")

    return missing_views, missing_functions


def _print_view_counts(missing_views):
    for schema, view_name in REQUIRED_VIEWS:
        qualified_name = f"{schema}.{view_name}"
        if qualified_name in missing_views:
            continue

        try:
            row = fetch_one(f"SELECT COUNT(1) AS CNT FROM {qualified_name}")
            print(f"View count {qualified_name}: {row['CNT']}")
        except Exception as exc:
            print(f"View count {qualified_name}: ERROR {exc}")


def _print_flask_smoke_status():
    app = create_app()
    app.testing = True
    client = app.test_client()

    response = client.get("/login")
    print(f"GET /login: {response.status_code}, bytes={len(response.data)}")

    with client.session_transaction() as session:
        session["USERNAME"] = "admin_user"
        session["ROLE"] = "Admin"
        session["SECURITYLEVEL"] = 9

    paths = ["/dashboard", "/db-status", "/wareneingang", "/lieferantenrechnung"]

    first_receipt = fetch_one(
        """
        SELECT TOP 1 GOODS_RECEIPT_ID
        FROM list_views.V_LIST_GOODS_RECEIPT
        ORDER BY GOODS_RECEIPT_ID
        """
    )
    if first_receipt:
        paths.append(f"/wareneingang/{first_receipt['GOODS_RECEIPT_ID']}/details")

    for path in paths:
        response = client.get(path)
        print(f"GET {path}: {response.status_code}, bytes={len(response.data)}")


def main():
    print("Read-only DB/App-Smoke-Test")
    settings = get_database_settings()
    print(
        "DB:",
        f"server={settings['server']}",
        f"database={settings['database']}",
        f"driver={settings['driver']}",
        f"encrypt={settings['encrypt']}",
    )
    print("Connection:", test_connection())

    missing_views, missing_functions = _print_missing_objects()
    _print_view_counts(missing_views)
    _print_flask_smoke_status()

    if missing_views or missing_functions:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
