from flask import Blueprint, render_template

from app.auth import require_security_level
from app.db import fetch_all, get_database_settings, is_database_configured, test_connection


db_status_bp = Blueprint("db_status", __name__)


REQUIRED_VIEWS = [
    ("list_views", "V_LIST_GOODS_RECEIPT"),
    ("list_views", "V_LIST_GOODS_RECEIPT_ITEM"),
    ("list_views", "V_LIST_SUPPLIER_INVOICE"),
    ("list_views", "V_LIST_SUPPLIER_INVOICE_ITEM"),
    ("list_views", "V_LIST_COMPONENTS_MOVEMENTS"),
    ("list_views", "V_LIST_PO_ITEM_FOR_GOODS_RECEIPT"),
    ("ins_views", "V_INS_GOODS_RECEIPT"),
    ("ins_views", "V_INS_GOODS_RECEIPT_ITEM"),
    ("ins_views", "V_INS_SUPPLIER_INVOICE"),
    ("ins_views", "V_INS_SUPPLIER_INVOICE_ITEM"),
    ("upd_views", "V_UPD_GOODS_RECEIPT"),
    ("upd_views", "V_UPD_GOODS_RECEIPT_ITEM"),
    ("upd_views", "V_UPD_SUPPLIER_INVOICE"),
    ("lov_views", "LOV_STATUS_GOODS_RECEIPT"),
    ("lov_views", "LOV_GOODS_CONDITION"),
    ("lov_views", "LOV_STATUS_SUPPLIER_INVOICE"),
    ("lov_views", "LOV_MOVEMENT_TYPE"),
]


REQUIRED_FUNCTIONS = [
    {
        "schema": "stored_func",
        "names": ["fn_g04_chk_GoodsReceipt"],
        "display_name": "fn_g04_chk_GoodsReceipt",
    },
    {
        "schema": "stored_func",
        "names": ["fn_g04_chk_GoodsReceiptItem"],
        "display_name": "fn_g04_chk_GoodsReceiptItem",
    },
    {
        "schema": "stored_func",
        "names": ["fn_g04_chk_GoodsReceiptBookingCondition"],
        "display_name": "fn_g04_chk_GoodsReceiptBookingCondition",
    },
    {
        "schema": "stored_func",
        "names": ["fn_g04_chk_SupplierInvoice"],
        "display_name": "fn_g04_chk_SupplierInvoice",
    },
    {
        "schema": "stored_func",
        "names": ["fn_g04_chk_SupplierInvoiceItem"],
        "display_name": "fn_g04_chk_SupplierInvoiceItem",
    },
    {
        "schema": "stored_func",
        "names": ["fn_g04_update_component_stock", "fn_update_component_stock"],
        "display_name": "fn_g04_update_component_stock oder fn_update_component_stock",
    },
]


def _view_exists(schema, view_name):
    result = fetch_all("""
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME
        FROM INFORMATION_SCHEMA.VIEWS
        WHERE TABLE_SCHEMA = ?
          AND TABLE_NAME = ?
    """, [schema, view_name])

    return len(result) > 0


def _routine_exists(schema, routine_names):
    placeholders = ", ".join("?" for _ in routine_names)
    result = fetch_all(f"""
        SELECT
            ROUTINE_SCHEMA,
            ROUTINE_NAME
        FROM INFORMATION_SCHEMA.ROUTINES
        WHERE ROUTINE_SCHEMA = ?
          AND ROUTINE_NAME IN ({placeholders})
    """, [schema, *routine_names])

    return len(result) > 0


@db_status_bp.route("/db-status")
@require_security_level(9)
def db_status():
    connection_status = {
        "configured": is_database_configured(),
        "connected": False,
        "message": "Datenbank ist nicht vollstaendig in der .env konfiguriert.",
        "settings": get_database_settings(),
    }

    view_status = []
    function_status = []

    if connection_status["configured"]:
        try:
            test_connection()
            connection_status["connected"] = True
            connection_status["message"] = "Verbindung zur Datenbank erfolgreich."

        except Exception as exc:
            connection_status["message"] = str(exc)

    if connection_status["connected"]:
        for schema, view_name in REQUIRED_VIEWS:
            try:
                exists = _view_exists(schema, view_name)

            except Exception:
                exists = False

            view_status.append({
                "schema": schema,
                "view_name": view_name,
                "exists": exists
            })

        for function in REQUIRED_FUNCTIONS:
            try:
                exists = _routine_exists(function["schema"], function["names"])

            except Exception:
                exists = False

            function_status.append({
                "schema": function["schema"],
                "function_name": function["display_name"],
                "exists": exists
            })

    return render_template(
        "db_status.html",
        connection_status=connection_status,
        view_status=view_status,
        function_status=function_status
    )
