from app.db import fetch_all, is_database_configured


goods_conditions = [
    {"CONDITION_ID": 401, "CONDITION_NAME": "BESCHAEDIGT"},
    {"CONDITION_ID": 402, "CONDITION_NAME": "FALSCHLIEFERUNG"},
    {"CONDITION_ID": 404, "CONDITION_NAME": "UNVOLLSTAENDIG"},
    {"CONDITION_ID": 405, "CONDITION_NAME": "UEBERLIEFERUNG"},
    {"CONDITION_ID": 406, "CONDITION_NAME": "KOMBINIERTE ABWEICHUNG"},
    {"CONDITION_ID": 407, "CONDITION_NAME": "WARE OK"},
    {"CONDITION_ID": 408, "CONDITION_NAME": "PRUEFUNG AUSSTEHEND"},
]


def get_goods_conditions():
    if is_database_configured():
        queries = [
            """
                SELECT
                    ID_CODE AS CONDITION_ID,
                    CODE_NAME AS CONDITION_NAME
                FROM lov_views.LOV_GOODS_CONDITION
                ORDER BY ID_CODE
            """,
            """
                SELECT
                    CODE_ID AS CONDITION_ID,
                    CONDITION_NAME
                FROM lov_views.LOV_GOODS_CONDITION
                ORDER BY CODE_ID
            """,
        ]

        last_error = None

        for query in queries:
            try:
                rows = fetch_all(query)

                if rows:
                    return rows

            except Exception as exc:
                last_error = exc

        print("LOV_GOODS_CONDITION konnte nicht geladen werden:")
        print(last_error)

    return goods_conditions


def get_condition_name(condition_id):
    for condition in get_goods_conditions():
        if condition["CONDITION_ID"] == int(condition_id):
            return condition["CONDITION_NAME"]

    return "UNBEKANNT"


def suggest_condition_id(ordered_qty, received_qty, damaged=False, wrong_delivery=False):
    ordered_qty = float(ordered_qty)
    received_qty = float(received_qty)

    if damaged and received_qty != ordered_qty:
        return 406

    if damaged:
        return 401

    if wrong_delivery:
        return 402

    if received_qty < ordered_qty:
        return 404

    if received_qty > ordered_qty:
        return 405

    if received_qty == ordered_qty:
        return 407

    return 408
