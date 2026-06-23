from datetime import date

from app.db import execute_query, fetch_all, fetch_one, is_database_configured
from app.services.db_check_service import run_optional_db_check
from app.services.goods_receipt_service import get_goods_receipt_by_id
from app.services.purchase_order_service import get_purchase_order_by_id


SUPPLIER_INVOICE_STATUS_NAMES = {
    300: "ERFASST",
    301: "AN BUCHHALTUNG UEBERMITTELT",
}


supplier_invoices = [
    {
        "INVOICE_ID": 3001,
        "GOODS_RECEIPT_ID": 1001,
        "PO_ID": 5001,
        "SUPPLIER_ID": 7001,
        "INVOICE_DATE": "2026-05-29",
        "DUE_DATE": "2026-06-12",
        "TOTAL_NET_AMOUNT": "1000.00",
        "TOTAL_VAT_AMOUNT": "190.00",
        "TOTAL_GROSS_AMOUNT": "1190.00",
        "INVOICE_STATUS": 300,
        "INVOICE_STATUS_NAME": "ERFASST",
    },
    {
        "INVOICE_ID": 3002,
        "GOODS_RECEIPT_ID": 1002,
        "PO_ID": 5002,
        "SUPPLIER_ID": 7002,
        "INVOICE_DATE": "2026-05-28",
        "DUE_DATE": "2026-06-11",
        "TOTAL_NET_AMOUNT": "2500.00",
        "TOTAL_VAT_AMOUNT": "475.00",
        "TOTAL_GROSS_AMOUNT": "2975.00",
        "INVOICE_STATUS": 301,
        "INVOICE_STATUS_NAME": "AN BUCHHALTUNG UEBERMITTELT",
    },
]


def _db_error(message, exc):
    print(message)
    print(exc)
    return False, f"{message}: {exc}"


def _parse_date(value, field_label):
    try:
        return True, date.fromisoformat(str(value))

    except (TypeError, ValueError):
        return False, f"{field_label} ist kein gueltiges Datum."


def _normalise_invoice(row):
    if row.get("INVOICE_STATUS") is not None:
        row["INVOICE_STATUS"] = int(row["INVOICE_STATUS"])

    if not row.get("INVOICE_STATUS_NAME"):
        row["INVOICE_STATUS_NAME"] = SUPPLIER_INVOICE_STATUS_NAMES.get(
            row.get("INVOICE_STATUS"),
            str(row.get("INVOICE_STATUS", "UNBEKANNT"))
        )

    return row


def _fetch_all_supplier_invoices_from_db():
    queries = [
        """
            SELECT *
            FROM list_views.V_LIST_SUPPLIER_INVOICE
            ORDER BY INVOICE_ID DESC
        """,
        """
            SELECT
                invoice.*,
                status_lov.CODE_NAME AS INVOICE_STATUS_NAME
            FROM list_views.V_LIST_SUPPLIER_INVOICE invoice
            LEFT JOIN lov_views.LOV_STATUS_SUPPLIER_INVOICE status_lov
                ON status_lov.ID_CODE = invoice.INVOICE_STATUS
            ORDER BY invoice.INVOICE_ID DESC
        """,
    ]

    last_error = None

    for query in queries:
        try:
            return [_normalise_invoice(row) for row in fetch_all(query)]

        except Exception as exc:
            last_error = exc

    print("DB-View fuer Lieferantenrechnungen noch nicht verfuegbar:")
    print(last_error)
    return None


def get_all_supplier_invoices():
    if is_database_configured():
        db_supplier_invoices = _fetch_all_supplier_invoices_from_db()

        if db_supplier_invoices is not None:
            return db_supplier_invoices

    return supplier_invoices


def _fetch_supplier_invoice_by_id_from_db(invoice_id):
    queries = [
        """
            SELECT *
            FROM list_views.V_LIST_SUPPLIER_INVOICE
            WHERE INVOICE_ID = ?
        """,
        """
            SELECT
                invoice.*,
                status_lov.CODE_NAME AS INVOICE_STATUS_NAME
            FROM list_views.V_LIST_SUPPLIER_INVOICE invoice
            LEFT JOIN lov_views.LOV_STATUS_SUPPLIER_INVOICE status_lov
                ON status_lov.ID_CODE = invoice.INVOICE_STATUS
            WHERE invoice.INVOICE_ID = ?
        """,
    ]

    last_error = None

    for query in queries:
        try:
            row = fetch_one(query, [invoice_id])

            if row is not None:
                return _normalise_invoice(row)

        except Exception as exc:
            last_error = exc

    print("Lieferantenrechnung konnte nicht aus der DB geladen werden:")
    print(last_error)
    return None


def get_supplier_invoice_by_id(invoice_id):
    try:
        invoice_id = int(invoice_id)

    except (TypeError, ValueError):
        return None

    if is_database_configured():
        db_invoice = _fetch_supplier_invoice_by_id_from_db(invoice_id)

        if db_invoice is not None:
            return db_invoice

    for invoice in supplier_invoices:
        if invoice["INVOICE_ID"] == invoice_id:
            return invoice

    return None


def _validate_invoice_dates(invoice_date, due_date):
    ok, parsed_invoice_date = _parse_date(invoice_date, "Das Rechnungsdatum")

    if not ok:
        return False, parsed_invoice_date

    ok, parsed_due_date = _parse_date(due_date, "Das Faelligkeitsdatum")

    if not ok:
        return False, parsed_due_date

    if parsed_invoice_date > date.today():
        return False, "Das Rechnungsdatum darf nicht in der Zukunft liegen."

    if parsed_due_date <= parsed_invoice_date:
        return False, "Das Faelligkeitsdatum muss nach dem Rechnungsdatum liegen."

    return True, ""


def _validate_totals(total_net_amount, total_vat_amount, total_gross_amount):
    try:
        net = float(total_net_amount)
        vat = float(total_vat_amount)
        gross = float(total_gross_amount)

    except (TypeError, ValueError):
        return False, "Netto, Umsatzsteuer und Brutto muessen gueltige Zahlen sein."

    if round(net + vat, 2) != round(gross, 2):
        return False, "Der Brutto-Betrag muss Netto-Betrag plus Umsatzsteuerbetrag entsprechen."

    return True, ""


def _supplier_id_for_goods_receipt(goods_receipt):
    supplier_id = goods_receipt.get("SUPPLIER_ID")

    if supplier_id:
        return supplier_id

    purchase_order = get_purchase_order_by_id(goods_receipt["PO_ID"])

    if purchase_order is None:
        return None

    return purchase_order.get("SUPPLIER_ID")


def create_supplier_invoice(
    goods_receipt_id,
    invoice_date,
    due_date,
    total_net_amount,
    total_vat_amount,
    total_gross_amount
):
    goods_receipt = get_goods_receipt_by_id(goods_receipt_id)

    if goods_receipt is None:
        return False, "Der ausgewaehlte Wareneingang existiert nicht."

    if int(goods_receipt["STATUS"]) != 202:
        return False, "Eine Lieferantenrechnung darf nur zu einem gebuchten Wareneingang erfasst werden."

    supplier_id = _supplier_id_for_goods_receipt(goods_receipt)

    if supplier_id is None:
        return False, "Zum Wareneingang konnte kein Lieferant ermittelt werden."

    ok, message = _validate_invoice_dates(invoice_date, due_date)

    if not ok:
        return False, message

    ok, message = _validate_totals(
        total_net_amount,
        total_vat_amount,
        total_gross_amount
    )

    if not ok:
        return False, message

    if is_database_configured():
        ok, message = run_optional_db_check(
            "stored_func.fn_g04_chk_SupplierInvoice",
            [supplier_id, goods_receipt["PO_ID"], invoice_date, due_date],
            "Lieferantenrechnung wurde durch die DB validiert."
        )

        if not ok:
            return False, message

        try:
            execute_query("""
                INSERT INTO ins_views.V_INS_SUPPLIER_INVOICE
                    (
                        GOODS_RECEIPT_ID,
                        PO_ID,
                        SUPPLIER_ID,
                        INVOICE_DATE,
                        DUE_DATE,
                        TOTAL_NET_AMOUNT,
                        TOTAL_VAT_AMOUNT,
                        TOTAL_GROSS_AMOUNT,
                        INVOICE_STATUS
                    )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                goods_receipt_id,
                goods_receipt["PO_ID"],
                supplier_id,
                invoice_date,
                due_date,
                total_net_amount,
                total_vat_amount,
                total_gross_amount,
                300,
            ])

            return True, "Lieferantenrechnung wurde in der Datenbank angelegt."

        except Exception as exc:
            return _db_error(
                "Lieferantenrechnung konnte nicht in der DB gespeichert werden",
                exc
            )

    new_id = max((invoice["INVOICE_ID"] for invoice in supplier_invoices), default=3000) + 1

    new_invoice = {
        "INVOICE_ID": new_id,
        "GOODS_RECEIPT_ID": int(goods_receipt_id),
        "PO_ID": goods_receipt["PO_ID"],
        "SUPPLIER_ID": supplier_id,
        "INVOICE_DATE": invoice_date,
        "DUE_DATE": due_date,
        "TOTAL_NET_AMOUNT": total_net_amount,
        "TOTAL_VAT_AMOUNT": total_vat_amount,
        "TOTAL_GROSS_AMOUNT": total_gross_amount,
        "INVOICE_STATUS": 300,
        "INVOICE_STATUS_NAME": "ERFASST",
    }

    supplier_invoices.append(new_invoice)

    return True, "Lieferantenrechnung wurde im Demo-Modus angelegt."


def transmit_supplier_invoice(invoice_id):
    invoice = get_supplier_invoice_by_id(invoice_id)

    if invoice is None:
        return False, "Lieferantenrechnung wurde nicht gefunden."

    if int(invoice["INVOICE_STATUS"]) != 300:
        return False, "Diese Rechnung wurde bereits uebermittelt oder kann nicht mehr geaendert werden."

    if is_database_configured():
        try:
            execute_query("""
                UPDATE upd_views.V_UPD_SUPPLIER_INVOICE
                SET INVOICE_STATUS = ?
                WHERE INVOICE_ID = ?
            """, [301, invoice_id])

            return True, "Lieferantenrechnung wurde in der Datenbank uebermittelt."

        except Exception as exc:
            return _db_error(
                "Lieferantenrechnung konnte nicht in der DB uebermittelt werden",
                exc
            )

    invoice["INVOICE_STATUS"] = 301
    invoice["INVOICE_STATUS_NAME"] = SUPPLIER_INVOICE_STATUS_NAMES[301]

    return True, "Lieferantenrechnung wurde im Demo-Modus uebermittelt."
