from flask import Blueprint, render_template

from app.auth import login_required
from app.services.goods_receipt_service import get_all_goods_receipts


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    goods_receipts = get_all_goods_receipts()
    critical_receipts = [
        goods_receipt for goods_receipt in goods_receipts
        if goods_receipt.get("STATUS") in (203, 204)
    ]

    return render_template(
        "dashboard.html",
        goods_receipts=goods_receipts,
        critical_receipts=critical_receipts
    )
