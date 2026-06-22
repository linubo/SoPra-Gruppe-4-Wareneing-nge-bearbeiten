from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.services.goods_receipt_service import (
    get_all_goods_receipts,
    create_goods_receipt,
    get_goods_receipt_by_id,
    get_items_by_goods_receipt_id,
    create_goods_receipt_item,
    update_goods_receipt_status,
)
from app.services.purchase_order_service import get_purchase_orders, get_purchase_order_items
from app.services.condition_service import get_goods_conditions
from app.auth import (
    can_change_goods_receipt_status,
    can_create_goods_receipt,
    can_edit_goods_receipt_items,
    login_required,
    require_security_level,
)

goods_receipt_bp = Blueprint("goods_receipt", __name__)


@goods_receipt_bp.route("/")
@login_required
def index():
    return redirect(url_for("dashboard.dashboard"))


@goods_receipt_bp.route("/wareneingang", methods=["GET", "POST"])
@require_security_level(2)
def goods_receipts():
    if request.method == "POST":
        if not can_create_goods_receipt():
            flash("Keine Berechtigung für diese Funktion.", "error")
            return redirect(url_for("goods_receipt.goods_receipts"))

        po_id = request.form.get("po_id")
        receipt_date = request.form.get("receipt_date")
        delivery_note_no = request.form.get("delivery_note_no")

        success, message = create_goods_receipt(
            po_id=po_id,
            receipt_date=receipt_date,
            delivery_note_no=delivery_note_no
        )

        flash(message, "success" if success else "error")
        return redirect(url_for("goods_receipt.goods_receipts"))

    return render_template(
        "goods_receipts.html",
        goods_receipts=get_all_goods_receipts(),
        purchase_orders=get_purchase_orders()
    )


@goods_receipt_bp.route("/wareneingaenge/<goods_receipt_id>")
@goods_receipt_bp.route("/wareneingang/<goods_receipt_id>")
@require_security_level(2)
def legacy_goods_receipt_detail(goods_receipt_id):
    return redirect(
        url_for(
            "goods_receipt.goods_receipt_detail",
            goods_receipt_id=goods_receipt_id
        )
    )


@goods_receipt_bp.route("/wareneingaenge/<goods_receipt_id>/details")
@goods_receipt_bp.route("/wareneingang/<goods_receipt_id>/details")
@goods_receipt_bp.route("/wareneingaenge/details/<goods_receipt_id>")
@goods_receipt_bp.route("/wareneingang/details/<goods_receipt_id>")
@require_security_level(2)
def goods_receipt_detail(goods_receipt_id):
    goods_receipt = get_goods_receipt_by_id(goods_receipt_id)

    if goods_receipt is None:
        flash("Wareneingang wurde nicht gefunden.", "error")
        return redirect(url_for("goods_receipt.goods_receipts"))

    items = get_items_by_goods_receipt_id(goods_receipt_id)
    conditions = get_goods_conditions()
    existing_po_item_ids = {
        int(item["PO_ITEM_ID"])
        for item in items
        if item.get("PO_ITEM_ID") is not None
           and item.get("PO_ID") == goods_receipt["PO_ID"]
    }
    purchase_order_items = [
        item for item in get_purchase_order_items(goods_receipt["PO_ID"])
        if item["PO_ITEM_ID"] not in existing_po_item_ids
    ]

    return render_template(
        "goods_receipt_detail.html",
        goods_receipt=goods_receipt,
        goods_receipt_items=items,
        conditions=conditions,
        purchase_order_items=purchase_order_items
    )


@goods_receipt_bp.route("/wareneingang/<goods_receipt_id>/position", methods=["POST"])
@require_security_level(2)
def add_goods_receipt_item(goods_receipt_id):
    if not can_edit_goods_receipt_items():
        flash("Keine Berechtigung für diese Funktion.", "error")
        return redirect(
            url_for(
                "goods_receipt.goods_receipt_detail",
                goods_receipt_id=goods_receipt_id
            )
        )

    po_item_id = request.form.get("po_item_id")
    article = request.form.get("article")
    ordered_qty = request.form.get("ordered_qty")
    received_qty = request.form.get("received_qty")
    condition_id = request.form.get("condition_id")
    damaged = request.form.get("damaged") == "on"
    wrong_delivery = request.form.get("wrong_delivery") == "on"

    success, message = create_goods_receipt_item(
        goods_receipt_id=goods_receipt_id,
        po_item_id=po_item_id,
        article=article,
        ordered_qty=ordered_qty,
        received_qty=received_qty,
        condition_id=condition_id,
        damaged=damaged,
        wrong_delivery=wrong_delivery
    )

    flash(message, "success" if success else "error")

    return redirect(
        url_for(
            "goods_receipt.goods_receipt_detail",
            goods_receipt_id=goods_receipt_id
        )
    )

@goods_receipt_bp.route("/wareneingang/<goods_receipt_id>/status", methods=["POST"])
@require_security_level(2)
def change_goods_receipt_status(goods_receipt_id):
    target_status = request.form.get("target_status")
    goods_receipt = get_goods_receipt_by_id(goods_receipt_id)

    if goods_receipt is None:
        flash("Wareneingang wurde nicht gefunden.", "error")
        return redirect(url_for("goods_receipt.goods_receipts"))

    if not can_change_goods_receipt_status(goods_receipt["STATUS"], target_status):
        flash("Keine Berechtigung für diese Funktion.", "error")
        return redirect(
            url_for(
                "goods_receipt.goods_receipt_detail",
                goods_receipt_id=goods_receipt_id
            )
        )

    success, message = update_goods_receipt_status(
        goods_receipt_id=goods_receipt_id,
        target_status=target_status
    )

    flash(message, "success" if success else "error")

    return redirect(
        url_for(
            "goods_receipt.goods_receipt_detail",
            goods_receipt_id=goods_receipt_id
        )
    )
