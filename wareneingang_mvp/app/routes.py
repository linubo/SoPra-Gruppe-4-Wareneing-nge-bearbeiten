from functools import wraps

from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from sqlalchemy import text
from sqlalchemy import text

from app.models import (
    PurchaseOrder,
    Component,
    GoodsReceipt,
    ComponentMovement,
    SupplierInvoice,
    EventLog,
    ReturnNotification
)

from app.services import (
    create_goods_receipt,
    start_goods_receipt_check,
    mark_goods_receipt_deviation,
    send_goods_receipt_to_clarification,
    create_return_for_goods_receipt,
    book_goods_receipt,
    cancel_booked_goods_receipt,
    create_supplier_invoice,
    transmit_supplier_invoice,
    update_goods_receipt_conditions_after_clarification,
    send_return_notification
)

main = Blueprint("main", __name__)

CLARIFICATION_DEADLINE_DAYS = 7


def get_clarification_started_at(receipt):
    clarification_event = EventLog.query.filter(
        EventLog.entity_type == "GoodsReceipt",
        EventLog.entity_id == receipt.id,
        EventLog.action == "STATUS_CHANGE",
        EventLog.description.like("%Klärung%")
    ).order_by(EventLog.created_at.desc()).first()

    if clarification_event:
        return clarification_event.created_at

    return receipt.receipt_date


def build_clarification_case(receipt):
    started_at = get_clarification_started_at(receipt)
    days_in_clarification = max((datetime.now() - started_at).days, 0)

    return {
        "receipt": receipt,
        "started_at": started_at,
        "days": days_in_clarification,
        "is_overdue": days_in_clarification >= CLARIFICATION_DEADLINE_DAYS
    }


def get_current_role():
    return session.get("user_role", "lager")


def role_required(*allowed_roles):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            current_role = get_current_role()

            if current_role not in allowed_roles:
                flash("Du hast mit deiner aktuellen Rolle keine Berechtigung für diese Aktion.")
                return redirect(url_for("main.index"))

            return function(*args, **kwargs)

        return wrapper

    return decorator


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/rolle", methods=["GET", "POST"])
def choose_role():
    if request.method == "POST":
        selected_role = request.form["role"]

        if selected_role not in ["lager", "management"]:
            flash("Ungültige Rolle ausgewählt.")
            return redirect(url_for("main.choose_role"))

        session["user_role"] = selected_role
        flash(f"Rolle wurde auf {selected_role.upper()} gesetzt.")
        return redirect(url_for("main.index"))

    return render_template("role.html")


@main.route("/bestellungen")
def purchase_orders():
    orders = PurchaseOrder.query.order_by(PurchaseOrder.created_at.desc()).all()
    return render_template("purchase_orders/list.html", orders=orders)


@main.route("/wareneingaenge")
def goods_receipts():
    receipts = GoodsReceipt.query.order_by(GoodsReceipt.receipt_date.desc()).all()
    return render_template("goods_receipts/list.html", receipts=receipts)


@main.route("/wareneingaenge/neu/<int:order_id>", methods=["GET", "POST"])
@role_required("lager")
def create_goods_receipt_view(order_id):
    order = PurchaseOrder.query.get_or_404(order_id)
    error = None

    if request.method == "POST":
        try:
            receipt = create_goods_receipt(order, request.form)
            return redirect(url_for("main.goods_receipt_detail", receipt_id=receipt.id))
        except ValueError as exception:
            error = str(exception)

    return render_template(
        "goods_receipts/create.html",
        order=order,
        error=error
    )


@main.route("/wareneingaenge/<int:receipt_id>")
def goods_receipt_detail(receipt_id):
    receipt = GoodsReceipt.query.get_or_404(receipt_id)
    return render_template("goods_receipts/detail.html", receipt=receipt)


@main.route("/wareneingaenge/<int:receipt_id>/pruefung-starten", methods=["POST"])
@role_required("lager")
def start_check(receipt_id):
    receipt = GoodsReceipt.query.get_or_404(receipt_id)

    try:
        start_goods_receipt_check(receipt)
        flash("Prüfung wurde gestartet.")
    except ValueError as exception:
        flash(str(exception))

    return redirect(url_for("main.goods_receipt_detail", receipt_id=receipt.id))


@main.route("/wareneingaenge/<int:receipt_id>/abweichung", methods=["POST"])
@role_required("lager")
def mark_deviation(receipt_id):
    receipt = GoodsReceipt.query.get_or_404(receipt_id)

    try:
        mark_goods_receipt_deviation(receipt)
        flash("Abweichung wurde dokumentiert.")
    except ValueError as exception:
        flash(str(exception))

    return redirect(url_for("main.goods_receipt_detail", receipt_id=receipt.id))


@main.route("/wareneingaenge/<int:receipt_id>/klaerung", methods=["POST"])
@role_required("lager")
def send_to_clarification(receipt_id):
    receipt = GoodsReceipt.query.get_or_404(receipt_id)

    try:
        send_goods_receipt_to_clarification(receipt)
        flash("Wareneingang wurde in Klärung gegeben.")
    except ValueError as exception:
        flash(str(exception))

    return redirect(url_for("main.goods_receipt_detail", receipt_id=receipt.id))

@main.route("/wareneingaenge/<int:receipt_id>/klaerung-bearbeiten", methods=["POST"])
@role_required("management")
def update_clarification(receipt_id):
    receipt = GoodsReceipt.query.get_or_404(receipt_id)

    try:
        update_goods_receipt_conditions_after_clarification(receipt, request.form)
        flash("Klärungsergebnis wurde gespeichert.")
    except ValueError as exception:
        flash(str(exception))

    return redirect(url_for("main.goods_receipt_detail", receipt_id=receipt.id))

@main.route("/wareneingaenge/<int:receipt_id>/retoure", methods=["POST"])
@role_required("management")
def create_return(receipt_id):
    receipt = GoodsReceipt.query.get_or_404(receipt_id)

    try:
        create_return_for_goods_receipt(receipt)
        flash("Retoure wurde veranlasst. Es wurde kein Lagerbestand erhöht.")
    except ValueError as exception:
        flash(str(exception))

    return redirect(url_for("main.goods_receipt_detail", receipt_id=receipt.id))


@main.route("/wareneingaenge/<int:receipt_id>/buchen", methods=["POST"])
@role_required("lager", "management")
def book_receipt(receipt_id):
    receipt = GoodsReceipt.query.get_or_404(receipt_id)

    current_role = get_current_role()

    if receipt.status == "IN_KLAERUNG" and current_role != "management":
        flash("Wareneingänge in Klärung dürfen nur vom Management entschieden werden.")
        return redirect(url_for("main.goods_receipt_detail", receipt_id=receipt.id))

    try:
        book_goods_receipt(receipt)
        flash("Wareneingang wurde gebucht. Der Lagerbestand wurde erhöht.")
    except ValueError as exception:
        flash(str(exception))

    return redirect(url_for("main.goods_receipt_detail", receipt_id=receipt.id))

@main.route("/wareneingaenge/<int:receipt_id>/stornieren", methods=["POST"])
@role_required("management")
def cancel_receipt(receipt_id):
    receipt = GoodsReceipt.query.get_or_404(receipt_id)

    try:
        cancel_booked_goods_receipt(receipt)
        flash("Wareneingang wurde storniert. Der Lagerbestand wurde reduziert.")
    except ValueError as exception:
        flash(str(exception))

    return redirect(url_for("main.goods_receipt_detail", receipt_id=receipt.id))

@main.route("/bestand")
def stock():
    components = Component.query.order_by(Component.name.asc()).all()
    return render_template("stock/list.html", components=components)


@main.route("/bestandsbewegungen")
def component_movements():
    movements = ComponentMovement.query.order_by(
        ComponentMovement.movement_date.desc()
    ).all()

    return render_template(
        "stock/movements.html",
        movements=movements
    )


@main.route("/lieferantenrechnungen")
def invoices():
    invoices_list = SupplierInvoice.query.order_by(
        SupplierInvoice.created_at.desc()
    ).all()

    booked_receipts = GoodsReceipt.query.filter_by(
        status="WARENEINGANG_GEBUCHT"
    ).order_by(GoodsReceipt.receipt_date.desc()).all()

    available_receipts = [
        receipt for receipt in booked_receipts
        if receipt.supplier_invoice is None
    ]

    return render_template(
        "invoices/list.html",
        invoices=invoices_list,
        available_receipts=available_receipts
    )


@main.route("/lieferantenrechnungen/neu/<int:receipt_id>", methods=["GET", "POST"])
@role_required("lager")
def create_invoice(receipt_id):
    receipt = GoodsReceipt.query.get_or_404(receipt_id)
    error = None

    if request.method == "POST":
        try:
            invoice = create_supplier_invoice(receipt, request.form)
            return redirect(url_for("main.invoice_detail", invoice_id=invoice.id))
        except ValueError as exception:
            error = str(exception)

    return render_template(
        "invoices/create.html",
        receipt=receipt,
        error=error
    )


@main.route("/lieferantenrechnungen/<int:invoice_id>")
def invoice_detail(invoice_id):
    invoice = SupplierInvoice.query.get_or_404(invoice_id)
    return render_template("invoices/detail.html", invoice=invoice)


@main.route("/lieferantenrechnungen/<int:invoice_id>/uebermitteln", methods=["POST"])
@role_required("lager")
def transmit_invoice(invoice_id):
    invoice = SupplierInvoice.query.get_or_404(invoice_id)

    try:
        transmit_supplier_invoice(invoice)
        flash("Lieferantenrechnung wurde an die Buchhaltung übermittelt.")
    except ValueError as exception:
        flash(str(exception))

    return redirect(url_for("main.invoice_detail", invoice_id=invoice.id))


@main.route("/ereignisprotokoll")
def event_log():
    events = EventLog.query.order_by(EventLog.created_at.desc()).all()

    return render_template(
        "event_log/list.html",
        events=events
    )


@main.route("/management")
@role_required("management")
def management_dashboard():
    receipts_total = GoodsReceipt.query.count()

    receipts_with_deviation = GoodsReceipt.query.filter_by(
        status="MIT_ABWEICHUNG"
    ).order_by(GoodsReceipt.receipt_date.desc()).all()

    receipts_in_clarification = GoodsReceipt.query.filter_by(
        status="IN_KLAERUNG"
    ).order_by(GoodsReceipt.receipt_date.desc()).all()

    clarification_cases = [
        build_clarification_case(receipt)
        for receipt in receipts_in_clarification
    ]

    critical_clarification_count = sum(
        1 for case in clarification_cases
        if case["is_overdue"]
    )

    receipts_booked_count = GoodsReceipt.query.filter_by(
        status="WARENEINGANG_GEBUCHT"
    ).count()

    receipts_returned_count = GoodsReceipt.query.filter_by(
        status="RETOURE_VERANLASST"
    ).count()

    open_invoices = SupplierInvoice.query.filter_by(
        status="ERFASST"
    ).order_by(SupplierInvoice.created_at.desc()).all()

    transmitted_invoice_count = SupplierInvoice.query.filter_by(
        status="AN_BUCHHALTUNG_UEBERMITTELT"
    ).count()

    return render_template(
        "management/dashboard.html",
        receipts_total=receipts_total,
        receipts_with_deviation=receipts_with_deviation,
        clarification_cases=clarification_cases,
        critical_clarification_count=critical_clarification_count,
        clarification_deadline_days=CLARIFICATION_DEADLINE_DAYS,
        receipts_booked_count=receipts_booked_count,
        receipts_returned_count=receipts_returned_count,
        open_invoices=open_invoices,
        transmitted_invoice_count=transmitted_invoice_count
    )

@main.route("/retourenmeldungen")
def return_notifications():
    notifications = ReturnNotification.query.order_by(
        ReturnNotification.created_at.desc()
    ).all()

    return render_template(
        "returns/list.html",
        notifications=notifications
    )


@main.route("/retourenmeldungen/<int:notification_id>")
def return_notification_detail(notification_id):
    notification = ReturnNotification.query.get_or_404(notification_id)

    return render_template(
        "returns/detail.html",
        notification=notification
    )


@main.route("/retourenmeldungen/<int:notification_id>/senden", methods=["POST"])
@role_required("management")
def send_return(notification_id):
    notification = ReturnNotification.query.get_or_404(notification_id)

    try:
        send_return_notification(notification)
        flash("Retourenmeldung wurde an den Lieferanten gesendet.")
    except ValueError as exception:
        flash(str(exception))

    return redirect(
        url_for("main.return_notification_detail", notification_id=notification.id)
    )

@main.route("/testfaelle")
def test_cases():
    return render_template("tests/list.html")

@main.route("/system/db-check")
def database_check():
    database_ok = False
    message = ""

    try:
        result = db.session.execute(text("SELECT 1")).scalar()
        database_ok = result == 1
        message = "Datenbankverbindung funktioniert."
    except Exception as exception:
        message = str(exception)

    return render_template(
        "system/db_check.html",
        database_ok=database_ok,
        message=message,
        database_mode=current_app.config.get("DATABASE_MODE"),
        database_label=current_app.config.get("DATABASE_LABEL")
    )