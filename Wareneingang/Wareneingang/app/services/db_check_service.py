from app.db import call_scalar_function, is_database_configured


def _is_ok(value):
    return str(value or "").strip().upper() == "OK"


def _as_function_list(function_names):
    if isinstance(function_names, str):
        return [function_names]

    return list(function_names)


def run_optional_db_check(function_names, params=None, success_message="DB-Pruefung OK"):
    if not is_database_configured():
        return True, "Demo-Modus: keine DB-Pruefung erforderlich."

    last_error = None

    for function_name in _as_function_list(function_names):
        try:
            result = call_scalar_function(function_name, params)

        except Exception as exc:
            last_error = exc
            continue

        if _is_ok(result):
            return True, success_message

        return False, str(result or "DB-Pruefung nicht bestanden.")

    print("Stored Function ist noch nicht verfuegbar:")
    print(last_error)
    return True, "Stored Function nicht verfuegbar; lokale Pruefung verwendet."


def run_optional_db_check_with_cursor(
    cursor,
    function_names,
    params=None,
    success_message="DB-Pruefung OK"
):
    last_error = None

    for function_name in _as_function_list(function_names):
        try:
            result = call_scalar_function(function_name, params, cursor=cursor)

        except Exception as exc:
            last_error = exc
            continue

        if _is_ok(result):
            return True, success_message

        return False, str(result or "DB-Pruefung nicht bestanden.")

    print("Stored Function ist noch nicht verfuegbar:")
    print(last_error)
    return True, "Stored Function nicht verfuegbar; lokale Pruefung verwendet."
