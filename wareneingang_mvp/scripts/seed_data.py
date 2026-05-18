import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.extensions import db
from app.models import Supplier, Component, PurchaseOrder, PurchaseOrderItem


app = create_app()


def seed_data():
    db.drop_all()
    db.create_all()

    supplier_1 = Supplier(
        supplier_number="SUP-001",
        name="BikeParts GmbH",
        email="rechnung@bikeparts.de"
    )

    supplier_2 = Supplier(
        supplier_number="SUP-002",
        name="Komponenten Müller",
        email="buchhaltung@komponenten-mueller.de"
    )

    chain = Component(
        component_number="KOMP-1001",
        name="Fahrradkette",
        stock=0
    )

    brake = Component(
        component_number="KOMP-1002",
        name="Scheibenbremse",
        stock=5
    )

    tire = Component(
        component_number="KOMP-1003",
        name="Mountainbike-Reifen",
        stock=12
    )

    db.session.add_all([supplier_1, supplier_2, chain, brake, tire])
    db.session.commit()

    po_1 = PurchaseOrder(
        po_number="PO-2026-001",
        supplier_id=supplier_1.id,
        status="OFFEN"
    )

    po_2 = PurchaseOrder(
        po_number="PO-2026-002",
        supplier_id=supplier_2.id,
        status="OFFEN"
    )

    db.session.add_all([po_1, po_2])
    db.session.commit()

    po_1_item_1 = PurchaseOrderItem(
        purchase_order_id=po_1.id,
        component_id=chain.id,
        ordered_quantity=50
    )

    po_1_item_2 = PurchaseOrderItem(
        purchase_order_id=po_1.id,
        component_id=brake.id,
        ordered_quantity=20
    )

    po_2_item_1 = PurchaseOrderItem(
        purchase_order_id=po_2.id,
        component_id=tire.id,
        ordered_quantity=30
    )

    db.session.add_all([po_1_item_1, po_1_item_2, po_2_item_1])
    db.session.commit()

    print("Testdaten wurden erfolgreich erstellt.")


if __name__ == "__main__":
    with app.app_context():
        seed_data()