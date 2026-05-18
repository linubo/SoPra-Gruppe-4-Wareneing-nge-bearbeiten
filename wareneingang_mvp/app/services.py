from datetime import datetime, date
from app.extensions import db
from app.models import (
    GoodsReceipt,
    GoodsReceiptItem,
    ComponentMovement,
    SupplierInvoice,
    SupplierInvoiceItem,
    EventLog,
    ReturnNotification
)


def generate_receipt_number():
    next_number = GoodsReceipt.query.count() + 1
    current_year = datetime.now().year
    return f"WE-{current_year}-{next_number:03d}"


def suggest_condition(received_quantity, open_quantity):
    if received_quantity == 0:
        return "PRUEFUNG_AUSSTEHEND"

    if received_quantity < open_quantity:
        return "UNVOLLSTAENDIG"

    if received_quantity > open_quantity:
        return "UEBERLIEFERUNG"

    return "WARE_OK"


def create_goods_receipt(order, form_data):
    receipt = GoodsReceipt(
        receipt_number=generate_receipt_number(),
        purchase_order_id=order.id,
        status="ERFASST",
        note=form_data.get("note", "")
    )

    db.session.add(receipt)
    db.session.flush()

    has_at_least_one_item = False

    for order_item in order.items:
        quantity_text = form_data.get(f"received_quantity_{order_item.id}", "0")

        if quantity_text == "":
            received_quantity = 0
        else:
            received_quantity = int(quantity_text)

        condition = form_data.get(
            f"condition_{order_item.id}",
            "AUTO"
        )

        if condition == "AUTO":
            condition = suggest_condition(
                received_quantity,
                order_item.open_quantity
            )

        if received_quantity < 0:
            raise ValueError("Die gelieferte Menge darf nicht negativ sein.")

        if received_quantity > 0:
            has_at_least_one_item = True

            receipt_item = GoodsReceiptItem(
                goods_receipt_id=receipt.id,
                purchase_order_item_id=order_item.id,
                ordered_quantity=order_item.ordered_quantity,
                received_quantity=received_quantity,
                condition=condition
            )

            db.session.add(receipt_item)

    if not has_at_least_one_item:
        db.session.rollback()
        raise ValueError("Es muss mindestens eine gelieferte Menge größer als 0 eingetragen werden.")

    log_event(
        "GoodsReceipt",
        receipt.id,
        "CREATE",
        f"Wareneingang {receipt.receipt_number} wurde erfasst."
    )

    db.session.commit()

    return receipt


def start_goods_receipt_check(receipt):
    if receipt.status != "ERFASST":
        raise ValueError("Die Prüfung kann nur im Status ERFASST gestartet werden.")

    receipt.status = "IN_PRUEFUNG"

    log_event(
        "GoodsReceipt",
        receipt.id,
        "STATUS_CHANGE",
        f"Prüfung für Wareneingang {receipt.receipt_number} wurde gestartet."
    )

    db.session.commit()


def mark_goods_receipt_deviation(receipt):
    if receipt.status != "IN_PRUEFUNG":
        raise ValueError("Abweichungen können nur im Status IN_PRUEFUNG markiert werden.")

    has_deviation = any(item.condition != "WARE_OK" for item in receipt.items)

    if not has_deviation:
        raise ValueError("Es gibt keine Abweichung. Alle Positionen sind WARE_OK.")

    receipt.status = "MIT_ABWEICHUNG"
    db.session.commit()


def send_goods_receipt_to_clarification(receipt):
    if receipt.status != "MIT_ABWEICHUNG":
        raise ValueError("Nur Wareneingänge mit Abweichung können in Klärung gegeben werden.")

    receipt.status = "IN_KLAERUNG"
    db.session.commit()


def create_return_for_goods_receipt(receipt):
    if receipt.status != "IN_KLAERUNG":
        raise ValueError("Eine Retoure kann nur aus dem Status IN_KLAERUNG veranlasst werden.")

    if receipt.return_notification is not None:
        raise ValueError("Für diesen Wareneingang existiert bereits eine Retourenmeldung.")

    reason = build_return_reason(receipt)
    message = build_return_message(receipt, reason)

    return_notification = ReturnNotification(
        return_number=generate_return_number(),
        goods_receipt_id=receipt.id,
        supplier_id=receipt.purchase_order.supplier_id,
        reason=reason,
        message=message,
        status="ERSTELLT"
    )

    db.session.add(return_notification)

    receipt.status = "RETOURE_VERANLASST"

    log_event(
        "GoodsReceipt",
        receipt.id,
        "RETURN",
        f"Für Wareneingang {receipt.receipt_number} wurde eine Retoure veranlasst."
    )

    log_event(
        "ReturnNotification",
        receipt.id,
        "CREATE",
        f"Retourenmeldung {return_notification.return_number} wurde erstellt."
    )

    db.session.commit()


def book_goods_receipt(receipt):
    if receipt.status not in ["IN_PRUEFUNG", "IN_KLAERUNG"]:
        raise ValueError("Der Wareneingang kann nur aus IN_PRUEFUNG oder IN_KLAERUNG gebucht werden.")

    for item in receipt.items:
        if item.condition != "WARE_OK":
            raise ValueError("Der Wareneingang kann nur gebucht werden, wenn alle Positionen WARE_OK sind.")

    for item in receipt.items:
        component = item.purchase_order_item.component
        component.stock += item.received_quantity

        movement = ComponentMovement(
            goods_receipt_id=receipt.id,
            component_id=component.id,
            quantity=item.received_quantity,
            movement_type="IN"
        )

        db.session.add(movement)

        receipt.status = "WARENEINGANG_GEBUCHT"

    update_purchase_order_status(receipt.purchase_order)

    log_event(
        "GoodsReceipt",
        receipt.id,
        "BOOK",
        f"Wareneingang {receipt.receipt_number} wurde gebucht und der Lagerbestand wurde erhöht."
    )

    db.session.commit()


def cancel_booked_goods_receipt(receipt):
    if receipt.status != "WARENEINGANG_GEBUCHT":
        raise ValueError("Nur gebuchte Wareneingänge können storniert werden.")

    if receipt.supplier_invoice is not None:
        raise ValueError(
            "Dieser Wareneingang kann nicht storniert werden, "
            "weil bereits eine Lieferantenrechnung existiert."
        )

    for item in receipt.items:
        component = item.purchase_order_item.component

        if component.stock < item.received_quantity:
            raise ValueError(
                f"Storno nicht möglich: Der Lagerbestand von {component.name} "
                f"ist kleiner als die zu stornierende Menge."
            )

    for item in receipt.items:
        component = item.purchase_order_item.component
        component.stock -= item.received_quantity

        movement = ComponentMovement(
            goods_receipt_id=receipt.id,
            component_id=component.id,
            quantity=item.received_quantity,
            movement_type="OUT"
        )

        db.session.add(movement)

    receipt.status = "STORNIERT"

    update_purchase_order_status(receipt.purchase_order)

    log_event(
        "GoodsReceipt",
        receipt.id,
        "CANCEL",
        f"Wareneingang {receipt.receipt_number} wurde storniert. "
        f"Der Lagerbestand wurde durch eine OUT-Bewegung reduziert."
    )

    db.session.commit()

def update_purchase_order_status(order):
    if order.total_open_quantity == 0:
        order.status = "ABGESCHLOSSEN"
    elif order.total_received_quantity > 0:
        order.status = "TEILWEISE_GELIEFERT"
    else:
        order.status = "OFFEN"


def generate_invoice_number():
    next_number = SupplierInvoice.query.count() + 1
    current_year = datetime.now().year
    return f"RE-{current_year}-{next_number:03d}"

def generate_return_number():
    next_number = ReturnNotification.query.count() + 1
    current_year = datetime.now().year
    return f"RET-{current_year}-{next_number:03d}"


def build_return_reason(receipt):
    conditions = []

    for item in receipt.items:
        if item.condition != "WARE_OK":
            conditions.append(item.condition)

    if not conditions:
        return "Retoure nach Klärung"

    unique_conditions = sorted(set(conditions))
    return ", ".join(unique_conditions)


def build_return_message(receipt, reason):
    supplier = receipt.purchase_order.supplier

    lines = [
        f"Retourenmeldung für Wareneingang {receipt.receipt_number}",
        "",
        f"Lieferant: {supplier.name}",
        f"Bestellung: {receipt.purchase_order.po_number}",
        f"Grund: {reason}",
        "",
        "Betroffene Positionen:"
    ]

    for item in receipt.items:
        lines.append(
            f"- {item.purchase_order_item.component.name}: "
            f"{item.received_quantity} Stück, Zustand: {item.condition}"
        )

    lines.extend([
        "",
        "Bitte prüfen Sie die Lieferung und stimmen Sie das weitere Vorgehen mit uns ab."
    ])

    return "\n".join(lines)

def parse_amount(value):
    return float(value.replace(",", "."))

def log_event(entity_type, entity_id, action, description):
    event = EventLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        description=description,
        created_by="demo_user"
    )

    db.session.add(event)

def create_supplier_invoice(receipt, form_data):
    if receipt.status != "WARENEINGANG_GEBUCHT":
        raise ValueError("Eine Lieferantenrechnung kann nur zu einem gebuchten Wareneingang erfasst werden.")

    if receipt.supplier_invoice is not None:
        raise ValueError("Zu diesem Wareneingang existiert bereits eine Lieferantenrechnung.")

    invoice_date = date.fromisoformat(form_data["invoice_date"])
    due_date = date.fromisoformat(form_data["due_date"])

    if invoice_date > date.today():
        raise ValueError("Das Rechnungsdatum darf nicht in der Zukunft liegen.")

    if due_date < invoice_date:
        raise ValueError("Das Fälligkeitsdatum darf nicht vor dem Rechnungsdatum liegen.")

    invoice = SupplierInvoice(
        invoice_number=form_data.get("invoice_number") or generate_invoice_number(),
        goods_receipt_id=receipt.id,
        supplier_id=receipt.purchase_order.supplier_id,
        invoice_date=invoice_date,
        due_date=due_date,
        status="ERFASST"
    )

    db.session.add(invoice)
    db.session.flush()

    total_net = 0
    total_vat = 0
    total_gross = 0

    for receipt_item in receipt.items:
        component = receipt_item.purchase_order_item.component

        quantity = int(form_data.get(f"quantity_{receipt_item.id}", receipt_item.received_quantity))
        unit_price_text = form_data.get(f"unit_price_{receipt_item.id}", "")
        discount_text = form_data.get(f"discount_{receipt_item.id}", "0")
        vat_text = form_data.get(f"vat_{receipt_item.id}", "19")

        if unit_price_text == "":
            db.session.rollback()
            raise ValueError(f"Für {component.name} muss ein Einzelpreis eingegeben werden.")

        unit_price = parse_amount(unit_price_text)
        discount = parse_amount(discount_text)
        vat = parse_amount(vat_text)

        if quantity <= 0:
            db.session.rollback()
            raise ValueError("Die Menge einer Rechnungsposition muss größer als 0 sein.")

        if unit_price < 0:
            db.session.rollback()
            raise ValueError("Der Einzelpreis darf nicht negativ sein.")

        if discount < 0 or discount > 100:
            db.session.rollback()
            raise ValueError("Der Rabatt muss zwischen 0 und 100 Prozent liegen.")

        if vat < 0 or vat > 30:
            db.session.rollback()
            raise ValueError("Die MwSt muss zwischen 0 und 30 Prozent liegen.")

        invoice_item = SupplierInvoiceItem(
            supplier_invoice_id=invoice.id,
            component_id=component.id,
            quantity=quantity,
            unit_price=unit_price,
            unit_discount_pct=discount,
            unit_vat_pct=vat
        )

        db.session.add(invoice_item)

        total_net += invoice_item.net_amount
        total_vat += invoice_item.vat_amount
        total_gross += invoice_item.gross_amount

    invoice.total_net_amount = round(total_net, 2)
    invoice.total_vat_amount = round(total_vat, 2)
    invoice.total_gross_amount = round(total_gross, 2)

    log_event(
        "SupplierInvoice",
        invoice.id,
        "CREATE",
        f"Lieferantenrechnung {invoice.invoice_number} wurde erfasst."
    )

    db.session.commit()

    return invoice


def transmit_supplier_invoice(invoice):
    if invoice.status != "ERFASST":
        raise ValueError("Nur Rechnungen im Status ERFASST können übermittelt werden.")

    invoice.status = "AN_BUCHHALTUNG_UEBERMITTELT"
    invoice.transmitted_at = datetime.now()

    log_event(
        "SupplierInvoice",
        invoice.id,
        "TRANSMIT",
        f"Lieferantenrechnung {invoice.invoice_number} wurde an die Buchhaltung übermittelt."
    )

    db.session.commit()
def update_goods_receipt_conditions_after_clarification(receipt, form_data):
    if receipt.status != "IN_KLAERUNG":
        raise ValueError("Klärungsergebnisse können nur im Status IN_KLAERUNG geändert werden.")

    for item in receipt.items:
        new_condition = form_data.get(f"condition_{item.id}")

        if new_condition not in [
            "WARE_OK",
            "BESCHAEDIGT",
            "FALSCHLIEFERUNG",
            "UNVOLLSTAENDIG",
            "UEBERLIEFERUNG",
            "KOMBINIERTE_ABWEICHUNG",
            "PRUEFUNG_AUSSTEHEND"
        ]:
            raise ValueError("Ungültiger Zustand ausgewählt.")

        item.condition = new_condition

    log_event(
        "GoodsReceipt",
        receipt.id,
        "CLARIFICATION_UPDATE",
        f"Klärungsergebnis für Wareneingang {receipt.receipt_number} wurde aktualisiert."
    )

    db.session.commit()

def send_return_notification(return_notification):
    if return_notification.status != "ERSTELLT":
        raise ValueError("Nur erstellte Retourenmeldungen können gesendet werden.")

    return_notification.status = "AN_LIEFERANT_GESENDET"
    return_notification.sent_at = datetime.now()

    log_event(
        "ReturnNotification",
        return_notification.id,
        "SEND",
        f"Retourenmeldung {return_notification.return_number} wurde an den Lieferanten gesendet."
    )

    db.session.commit()