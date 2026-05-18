from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import (
    PurchaseOrder,
    Component,
    GoodsReceipt,
    ComponentMovement,
    SupplierInvoice,
    EventLog
)
from app.services import (
    create_goods_receipt,
    start_goods_receipt_check,
    mark_goods_receipt_deviation,
    send_goods_receipt_to_clarification,
    create_return_for_goods_receipt,
    book_goods_receipt,
    create_supplier_invoice,
    transmit_supplier_invoice
)

main = Blueprint("main", __name__)


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/bestellungen")
def purchase_orders():
    orders = PurchaseOrder.query.order_by(PurchaseOrder.created_at.desc()).all()
    return render_template("purchase_orders/list.html", orders=orders)


@main.route("/wareneingaenge")
def goods_receipts():
    receipts = GoodsReceipt.query.order_by(GoodsReceipt.receipt_date.desc()).all()
    return render_template("goods_receipts/list.html", receipts=receipts)


@main.route("/wareneingaenge/neu/<int:order_id>", methods=["GET", "POST"])
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
def start_check(receipt_id):
    receipt = GoodsReceipt.query.get_or_404(receipt_id)

    try:
        start_goods_receipt_check(receipt)
        flash("Prüfung wurde gestartet.")
    except ValueError as exception:
        flash(str(exception))

    return redirect(url_for("main.goods_receipt_detail", receipt_id=receipt.id))


@main.route("/wareneingaenge/<int:receipt_id>/abweichung", methods=["POST"])
def mark_deviation(receipt_id):
    receipt = GoodsReceipt.query.get_or_404(receipt_id)

    try:
        mark_goods_receipt_deviation(receipt)
        flash("Abweichung wurde dokumentiert.")
    except ValueError as exception:
        flash(str(exception))

    return redirect(url_for("main.goods_receipt_detail", receipt_id=receipt.id))


@main.route("/wareneingaenge/<int:receipt_id>/klaerung", methods=["POST"])
def send_to_clarification(receipt_id):
    receipt = GoodsReceipt.query.get_or_404(receipt_id)

    try:
        send_goods_receipt_to_clarification(receipt)
        flash("Wareneingang wurde in Klärung gegeben.")
    except ValueError as exception:
        flash(str(exception))

    return redirect(url_for("main.goods_receipt_detail", receipt_id=receipt.id))


@main.route("/wareneingaenge/<int:receipt_id>/retoure", methods=["POST"])
def create_return(receipt_id):
    receipt = GoodsReceipt.query.get_or_404(receipt_id)

    try:
        create_return_for_goods_receipt(receipt)
        flash("Retoure wurde veranlasst. Es wurde kein Lagerbestand erhöht.")
    except ValueError as exception:
        flash(str(exception))

    return redirect(url_for("main.goods_receipt_detail", receipt_id=receipt.id))


@main.route("/wareneingaenge/<int:receipt_id>/buchen", methods=["POST"])
def book_receipt(receipt_id):
    receipt = GoodsReceipt.query.get_or_404(receipt_id)

    try:
        book_goods_receipt(receipt)
        flash("Wareneingang wurde gebucht. Der Lagerbestand wurde erhöht.")
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