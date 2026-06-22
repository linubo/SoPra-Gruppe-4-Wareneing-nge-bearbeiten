from datetime import date

from app.db import execute_query, execute_transaction, fetch_all, fetch_one, is_database_configured
from app.services.condition_service import get_condition_name, suggest_condition_id
from app.services.db_check_service import (
    run_optional_db_check,
    run_optional_db_check_with_cursor,
)
from app.services.purchase_order_service import (
    get_purchase_order_by_id,
    get_purchase_order_item,
    get_purchase_order_item_by_item_id,
)


GOODS_RECEIPT_STATUS_NAMES = {
    200: "ERFASST",
    201: "IN PRUEFUNG",
    202: "WARENEINGANG GEBUCHT",
    203: "MIT ABWEICHUNG",
    204: "IN KLAERUNG",
    205: "RETOURE VERANLASST",
}


LEGACY_GOODS_RECEIPT_STATUS_MAP = {
    130: 200,
    131: 203,
    132: 202,
}


LEGACY_GOODS_CONDITION_MAP = {
    140: 407,
    141: 401,
    142: 404,
}


ALLOWED_STATUS_TRANSITIONS = {
    200: [201],
    201: [202, 203],
    203: [204],
    204: [202, 205],
}


goods_receipts = [
    {
        "GOODS_RECEIPT_ID": 1001,
        "PO_ID": 5001,
        "SUPPLIER_ID": 7001,
        "RECEIPT_DATE": "2026-05-29",
        "DELIVERY_NOTE_NO": "LS-2026-001",
        "STATUS": 200,
        "STATUS_NAME": "ERFASST",
    },
    {
        "GOODS_RECEIPT_ID": 1002,
        "PO_ID": 5002,
        "SUPPLIER_ID": 7002,
        "RECEIPT_DATE": "2026-05-28",
        "DELIVERY_NOTE_NO": "LS-2026-002",
        "STATUS": 201,
        "STATUS_NAME": "IN PRUEFUNG",
    },
]


goods_receipt_items = [
    {
        "GOODS_RECEIPT_ITEM_ID": 9001,
        "GOODS_RECEIPT_ID": 1001,
        "PO_ID": 5001,
        "PO_ITEM_ID": 8001,
        "ARTICLE": "Schraube M8",
        "ORDERED_QTY": 100,
        "RECEIVED_QTY": 100,
        "CONDITION_ID": 407,
        "CONDITION_NAME": "WARE OK",
    },
    {
        "GOODS_RECEIPT_ITEM_ID": 9002,
        "GOODS_RECEIPT_ID": 1002,
        "PO_ID": 5002,
        "PO_ITEM_ID": 8002,
        "ARTICLE": "Metallplatte",
        "ORDERED_QTY": 50,
        "RECEIVED_QTY": 45,
        "CONDITION_ID": 404,
        "CONDITION_NAME": "UNVOLLSTAENDIG",
    },
]


def _db_error(message, exc):
    print(message)
    print(exc)
    return False, f"{message}: {exc}"


def _date_is_not_future(date_value, field_label):
    try:
        parsed_date = date.fromisoformat(str(date_value))

    except (TypeError, ValueError):
        return False, f"{field_label} ist kein gueltiges Datum."

    if parsed_date > date.today():
        return False, f"{field_label} darf nicht in der Zukunft liegen."

    return True, ""


def _normalise_goods_receipt(row):
    if row.get("STATUS") is not None:
        db_status = int(row["STATUS"])
        row["DB_STATUS"] = db_status
        row["STATUS"] = LEGACY_GOODS_RECEIPT_STATUS_MAP.get(db_status, db_status)

    row["STATUS_NAME"] = GOODS_RECEIPT_STATUS_NAMES.get(
        row.get("STATUS"),
        row.get("STATUS_NAME") or str(row.get("STATUS", "UNBEKANNT"))
    )

    if not row.get("SUPPLIER_ID") and row.get("PO_ID"):
        purchase_order = get_purchase_order_by_id(row["PO_ID"])

        if purchase_order is not None:
            row["SUPPLIER_ID"] = purchase_order.get("SUPPLIER_ID")

    row["DELIVERY_NOTE_NO"] = (
        row.get("DELIVERY_NOTE_NO")
        or row.get("DELIVERY_NOTE_NUMBER")
        or ""
    )
    return row


def _normalise_goods_receipt_item(row):
    if row.get("CONDITION_ID") is not None:
        db_condition_id = int(row["CONDITION_ID"])
        row["DB_CONDITION_ID"] = db_condition_id
        row["CONDITION_ID"] = LEGACY_GOODS_CONDITION_MAP.get(
            db_condition_id,
            db_condition_id
        )

    if not row.get("CONDITION_NAME") and row.get("CONDITION_ID") is not None:
        row["CONDITION_NAME"] = get_condition_name(row["CONDITION_ID"])

    if not row.get("ARTICLE"):
        purchase_order_item = None

        if row.get("PO_ID") and row.get("PO_ITEM_ID"):
            purchase_order_item = get_purchase_order_item(
                row["PO_ID"],
                row["PO_ITEM_ID"]
            )

        if purchase_order_item is None and row.get("PO_ITEM_ID"):
            purchase_order_item = get_purchase_order_item_by_item_id(
                row["PO_ITEM_ID"]
            )

        row["ARTICLE"] = (
            row.get("COMPONENT_NAME")
            or row.get("ARTICLE_NAME")
            or (purchase_order_item or {}).get("ARTICLE")
            or row.get("COMPONENT_ID")
            or row.get("ID_COMPONENT")
            or ""
        )

    return row


def _fetch_all_goods_receipts_from_db():
    queries = [
        """
            SELECT *
            FROM list_views.V_LIST_GOODS_RECEIPT
            ORDER BY GOODS_RECEIPT_ID DESC
        """,
        """
            SELECT
                gr.*,
                status_lov.CODE_NAME AS STATUS_NAME
            FROM list_views.V_LIST_GOODS_RECEIPT gr
            LEFT JOIN lov_views.LOV_STATUS_GOODS_RECEIPT status_lov
                ON status_lov.ID_CODE = gr.STATUS
            ORDER BY gr.GOODS_RECEIPT_ID DESC
        """,
    ]

    last_error = None

    for query in queries:
        try:
            return [_normalise_goods_receipt(row) for row in fetch_all(query)]

        except Exception as exc:
            last_error = exc

    print("DB-View fuer Wareneingaenge noch nicht verfuegbar:")
    print(last_error)
    return None


def get_all_goods_receipts():
    if is_database_configured():
        db_goods_receipts = _fetch_all_goods_receipts_from_db()

        if db_goods_receipts is not None:
            return db_goods_receipts

    return goods_receipts


def create_goods_receipt(po_id, receipt_date, delivery_note_no):
    try:
        po_id = int(po_id)

    except (TypeError, ValueError):
        return False, "Bitte eine gueltige Bestellung auswaehlen."

    purchase_order = get_purchase_order_by_id(po_id)

    if purchase_order is None and not is_database_configured():
        return False, "Die ausgewaehlte Bestellung existiert nicht."

    ok, message = _date_is_not_future(receipt_date, "Das Wareneingangsdatum")

    if not ok:
        return False, message

    if is_database_configured():
        ok, message = run_optional_db_check(
            "stored_func.fn_g04_chk_GoodsReceipt",
            [po_id, receipt_date],
            "Wareneingang wurde durch die DB validiert."
        )

        if not ok:
            return False, message

        try:
            insert_queries = [
                """
                    INSERT INTO ins_views.V_INS_GOODS_RECEIPT
                        (PO_ID, RECEIPT_DATE, DELIVERY_NOTE_NO, STATUS)
                    VALUES (?, ?, ?, ?)
                """,
                """
                    INSERT INTO ins_views.V_INS_GOODS_RECEIPT
                        (PO_ID, RECEIPT_DATE, DELIVERY_NOTE_NUMBER, STATUS)
                    VALUES (?, ?, ?, ?)
                """,
            ]

            last_error = None

            for query in insert_queries:
                try:
                    execute_query(query, [po_id, receipt_date, delivery_note_no, 200])
                    return True, "Wareneingang wurde in der Datenbank angelegt."

                except Exception as exc:
                    last_error = exc

            raise last_error

        except Exception as exc:
            return _db_error("Wareneingang konnte nicht in der DB gespeichert werden", exc)

    new_id = max((gr["GOODS_RECEIPT_ID"] for gr in goods_receipts), default=1000) + 1

    new_goods_receipt = {
        "GOODS_RECEIPT_ID": new_id,
        "PO_ID": int(po_id),
        "SUPPLIER_ID": purchase_order["SUPPLIER_ID"],
        "RECEIPT_DATE": receipt_date,
        "DELIVERY_NOTE_NO": delivery_note_no,
        "STATUS": 200,
        "STATUS_NAME": "ERFASST",
    }

    goods_receipts.append(new_goods_receipt)

    return True, "Wareneingang wurde im Demo-Modus angelegt."


def _fetch_goods_receipt_by_id_from_db(goods_receipt_id):
    queries = [
        """
            SELECT *
            FROM list_views.V_LIST_GOODS_RECEIPT
            WHERE GOODS_RECEIPT_ID = ?
        """,
        """
            SELECT
                gr.*,
                status_lov.CODE_NAME AS STATUS_NAME
            FROM list_views.V_LIST_GOODS_RECEIPT gr
            LEFT JOIN lov_views.LOV_STATUS_GOODS_RECEIPT status_lov
                ON status_lov.ID_CODE = gr.STATUS
            WHERE gr.GOODS_RECEIPT_ID = ?
        """,
    ]

    last_error = None

    for query in queries:
        try:
            row = fetch_one(query, [goods_receipt_id])

            if row is not None:
                return _normalise_goods_receipt(row)

        except Exception as exc:
            last_error = exc

    print("Wareneingang konnte nicht aus der DB geladen werden:")
    print(last_error)
    return None


def get_goods_receipt_by_id(goods_receipt_id):
    try:
        goods_receipt_id = int(goods_receipt_id)

    except (TypeError, ValueError):
        return None

    if is_database_configured():
        db_goods_receipt = _fetch_goods_receipt_by_id_from_db(goods_receipt_id)

        if db_goods_receipt is not None:
            return db_goods_receipt

    for gr in goods_receipts:
        if gr["GOODS_RECEIPT_ID"] == goods_receipt_id:
            return gr

    return None


def _fetch_items_by_goods_receipt_id_from_db(goods_receipt_id):
    queries = [
        """
            SELECT *
            FROM list_views.V_LIST_GOODS_RECEIPT_ITEM
            WHERE GOODS_RECEIPT_ID = ?
            ORDER BY GOODS_RECEIPT_ITEM_ID
        """,
        """
            SELECT
                item.*,
                condition_lov.CODE_NAME AS CONDITION_NAME
            FROM list_views.V_LIST_GOODS_RECEIPT_ITEM item
            LEFT JOIN lov_views.LOV_GOODS_CONDITION condition_lov
                ON condition_lov.ID_CODE = item.CONDITION_ID
            WHERE item.GOODS_RECEIPT_ID = ?
            ORDER BY item.GOODS_RECEIPT_ITEM_ID
        """,
    ]

    last_error = None

    for query in queries:
        try:
            return [
                _normalise_goods_receipt_item(row)
                for row in fetch_all(query, [goods_receipt_id])
            ]

        except Exception as exc:
            last_error = exc

    print("DB-View fuer Wareneingangspositionen noch nicht verfuegbar:")
    print(last_error)
    return None


def get_items_by_goods_receipt_id(goods_receipt_id):
    try:
        goods_receipt_id = int(goods_receipt_id)

    except (TypeError, ValueError):
        return []

    if is_database_configured():
        db_items = _fetch_items_by_goods_receipt_id_from_db(goods_receipt_id)

        if db_items is not None:
            return db_items

    return [
        item for item in goods_receipt_items
        if item["GOODS_RECEIPT_ID"] == goods_receipt_id
    ]


def create_goods_receipt_item(
    goods_receipt_id,
    po_item_id,
    article,
    ordered_qty,
    received_qty,
    condition_id=None,
    damaged=False,
    wrong_delivery=False
):
    try:
        goods_receipt_id = int(goods_receipt_id)
        po_item_id = int(po_item_id)

    except (TypeError, ValueError):
        return False, "Wareneingang und Bestellposition muessen gueltige IDs sein."

    goods_receipt = get_goods_receipt_by_id(goods_receipt_id)

    if goods_receipt is None:
        return False, "Der ausgewaehlte Wareneingang existiert nicht."

    purchase_order_item = get_purchase_order_item(goods_receipt["PO_ID"], po_item_id)

    if purchase_order_item is None:
        return False, "Die ausgewaehlte Bestellposition gehoert nicht zu diesem Wareneingang."

    article = purchase_order_item["ARTICLE"]
    ordered_qty = purchase_order_item["ORDERED_QTY"]

    try:
        ordered_qty_value = float(ordered_qty)
        received_qty_value = float(received_qty)

    except (TypeError, ValueError):
        return False, "Bestellte und gelieferte Menge muessen gueltige Zahlen sein."

    if ordered_qty_value <= 0:
        return False, "Die bestellte Menge muss groesser als 0 sein."

    if received_qty_value < 0:
        return False, "Die gelieferte Menge darf nicht negativ sein."

    if not condition_id:
        condition_id = suggest_condition_id(
            ordered_qty=ordered_qty,
            received_qty=received_qty,
            damaged=damaged,
            wrong_delivery=wrong_delivery
        )

    condition_id = int(condition_id)

    if is_database_configured():
        ok, message = run_optional_db_check(
            "stored_func.fn_g04_chk_GoodsReceiptItem",
            [
                goods_receipt["PO_ID"],
                po_item_id,
                ordered_qty,
                received_qty,
                condition_id,
            ],
            "Wareneingangsposition wurde durch die DB validiert."
        )

        if not ok:
            return False, message

        try:
            execute_query("""
                INSERT INTO ins_views.V_INS_GOODS_RECEIPT_ITEM
                    (
                        GOODS_RECEIPT_ID,
                        PO_ID,
                        PO_ITEM_ID,
                        ORDERED_QTY,
                        RECEIVED_QTY,
                        CONDITION_ID
                    )
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                goods_receipt_id,
                goods_receipt["PO_ID"],
                po_item_id,
                ordered_qty,
                received_qty,
                condition_id,
            ])

            return True, "Wareneingangsposition wurde in der Datenbank angelegt."

        except Exception as exc:
            return _db_error(
                "Wareneingangsposition konnte nicht in der DB gespeichert werden",
                exc
            )

    new_id = max(
        (item["GOODS_RECEIPT_ITEM_ID"] for item in goods_receipt_items),
        default=9000
    ) + 1

    new_item = {
        "GOODS_RECEIPT_ITEM_ID": new_id,
        "GOODS_RECEIPT_ID": int(goods_receipt_id),
        "PO_ID": goods_receipt["PO_ID"],
        "PO_ITEM_ID": int(po_item_id),
        "ARTICLE": article,
        "ORDERED_QTY": float(ordered_qty),
        "RECEIVED_QTY": float(received_qty),
        "CONDITION_ID": condition_id,
        "CONDITION_NAME": get_condition_name(condition_id),
    }

    goods_receipt_items.append(new_item)

    return True, "Wareneingangsposition wurde im Demo-Modus angelegt."


def all_items_are_ok(goods_receipt_id):
    items = get_items_by_goods_receipt_id(goods_receipt_id)

    if len(items) == 0:
        return False

    for item in items:
        if item["CONDITION_ID"] != 407:
            return False

    return True


def has_any_deviation(goods_receipt_id):
    items = get_items_by_goods_receipt_id(goods_receipt_id)

    for item in items:
        if item["CONDITION_ID"] != 407:
            return True

    return False


def _update_goods_receipt_status_in_db(goods_receipt_id, target_status):
    def transaction(cursor):
        ok, message = run_optional_db_check_with_cursor(
            cursor,
            "stored_func.fn_g04_chk_GoodsReceiptBookingCondition",
            [goods_receipt_id, target_status],
            "Buchungsbedingung wurde durch die DB validiert."
        )

        if not ok:
            raise ValueError(message)

        cursor.execute("""
            UPDATE upd_views.V_UPD_GOODS_RECEIPT
            SET STATUS = ?
            WHERE GOODS_RECEIPT_ID = ?
        """, target_status, goods_receipt_id)

        if int(target_status) == 202:
            ok, message = run_optional_db_check_with_cursor(
                cursor,
                [
                    "stored_func.fn_g04_update_component_stock",
                    "stored_func.fn_update_component_stock",
                ],
                [goods_receipt_id],
                "Bestand wurde durch die DB aktualisiert."
            )

            if not ok:
                raise ValueError(message)

    execute_transaction(transaction)


def update_goods_receipt_status(goods_receipt_id, target_status):
    goods_receipt = get_goods_receipt_by_id(goods_receipt_id)

    if goods_receipt is None:
        return False, "Wareneingang wurde nicht gefunden."

    try:
        current_status = int(goods_receipt["STATUS"])
        target_status = int(target_status)

    except (TypeError, ValueError):
        return False, "Der Zielstatus ist ungueltig."

    if current_status not in ALLOWED_STATUS_TRANSITIONS:
        return False, "Fuer den aktuellen Status ist kein weiterer Statuswechsel erlaubt."

    if target_status not in ALLOWED_STATUS_TRANSITIONS[current_status]:
        return False, "Dieser Statuswechsel ist fachlich nicht erlaubt."

    if current_status == 201 and target_status == 202:
        if not all_items_are_ok(goods_receipt_id):
            return False, "Direktes Buchen ist nur moeglich, wenn alle Positionen CONDITION_ID 407 WARE OK haben."

    if current_status == 201 and target_status == 203:
        if not has_any_deviation(goods_receipt_id):
            return False, "Abweichung dokumentieren ist nur moeglich, wenn mindestens eine Position eine Abweichung hat."

    if is_database_configured():
        try:
            _update_goods_receipt_status_in_db(goods_receipt_id, target_status)

        except Exception as exc:
            return _db_error("Status konnte nicht in der DB geaendert werden", exc)

        if target_status == 202:
            return True, "Wareneingang wurde in der Datenbank gebucht."

        if target_status == 205:
            return True, "Retoure wurde in der Datenbank veranlasst."

        return True, f"Status wurde in der Datenbank auf {GOODS_RECEIPT_STATUS_NAMES[target_status]} gesetzt."

    goods_receipt["STATUS"] = target_status
    goods_receipt["STATUS_NAME"] = GOODS_RECEIPT_STATUS_NAMES[target_status]

    if target_status == 202:
        return True, "Wareneingang wurde im Demo-Modus gebucht."

    if target_status == 205:
        return True, "Retoure wurde im Demo-Modus veranlasst. Es erfolgt kein Lagerzugang."

    return True, f"Status wurde auf {GOODS_RECEIPT_STATUS_NAMES[target_status]} gesetzt."
