from datetime import datetime, date
from app.extensions import db


class Supplier(db.Model):
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    supplier_number = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))

    purchase_orders = db.relationship("PurchaseOrder", back_populates="supplier")
    supplier_invoices = db.relationship("SupplierInvoice", back_populates="supplier")


class Component(db.Model):
    __tablename__ = "components"

    id = db.Column(db.Integer, primary_key=True)
    component_number = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)

    order_items = db.relationship("PurchaseOrderItem", back_populates="component")
    movements = db.relationship("ComponentMovement", back_populates="component")


class PurchaseOrder(db.Model):
    __tablename__ = "purchase_orders"

    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(50), nullable=False, unique=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="OFFEN")

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    supplier = db.relationship("Supplier", back_populates="purchase_orders")
    items = db.relationship(
        "PurchaseOrderItem",
        back_populates="purchase_order",
        cascade="all, delete-orphan"
    )
    goods_receipts = db.relationship(
        "GoodsReceipt",
        back_populates="purchase_order",
        cascade="all, delete-orphan"
    )

    @property
    def total_ordered_quantity(self):
        return sum(item.ordered_quantity for item in self.items)

    @property
    def total_received_quantity(self):
        return sum(item.received_quantity for item in self.items)

    @property
    def total_open_quantity(self):
        return max(self.total_ordered_quantity - self.total_received_quantity, 0)


class PurchaseOrderItem(db.Model):
    __tablename__ = "purchase_order_items"

    id = db.Column(db.Integer, primary_key=True)

    purchase_order_id = db.Column(
        db.Integer,
        db.ForeignKey("purchase_orders.id"),
        nullable=False
    )

    component_id = db.Column(
        db.Integer,
        db.ForeignKey("components.id"),
        nullable=False
    )

    ordered_quantity = db.Column(db.Integer, nullable=False)

    purchase_order = db.relationship("PurchaseOrder", back_populates="items")
    component = db.relationship("Component", back_populates="order_items")
    goods_receipt_items = db.relationship(
        "GoodsReceiptItem",
        back_populates="purchase_order_item"
    )

    @property
    def received_quantity(self):
        ignored_statuses = ["STORNIERT", "RETOURE_VERANLASST"]

        return sum(
            item.received_quantity
            for item in self.goods_receipt_items
            if item.goods_receipt.status not in ignored_statuses
    )

    @property
    def open_quantity(self):
        return max(self.ordered_quantity - self.received_quantity, 0)


class GoodsReceipt(db.Model):
    __tablename__ = "goods_receipts"

    id = db.Column(db.Integer, primary_key=True)
    receipt_number = db.Column(db.String(50), nullable=False, unique=True)

    purchase_order_id = db.Column(
        db.Integer,
        db.ForeignKey("purchase_orders.id"),
        nullable=False
    )

    receipt_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    status = db.Column(db.String(50), nullable=False, default="ERFASST")
    note = db.Column(db.String(255))

    purchase_order = db.relationship("PurchaseOrder", back_populates="goods_receipts")
    items = db.relationship(
        "GoodsReceiptItem",
        back_populates="goods_receipt",
        cascade="all, delete-orphan"
    )

    supplier_invoice = db.relationship(
        "SupplierInvoice",
        back_populates="goods_receipt",
        uselist=False
    )

    return_notification = db.relationship(
        "ReturnNotification",
        back_populates="goods_receipt",
        uselist=False
    )


class GoodsReceiptItem(db.Model):
    __tablename__ = "goods_receipt_items"

    id = db.Column(db.Integer, primary_key=True)

    goods_receipt_id = db.Column(
        db.Integer,
        db.ForeignKey("goods_receipts.id"),
        nullable=False
    )

    purchase_order_item_id = db.Column(
        db.Integer,
        db.ForeignKey("purchase_order_items.id"),
        nullable=False
    )

    ordered_quantity = db.Column(db.Integer, nullable=False)
    received_quantity = db.Column(db.Integer, nullable=False)
    condition = db.Column(db.String(50), nullable=False, default="PRUEFUNG_AUSSTEHEND")

    goods_receipt = db.relationship("GoodsReceipt", back_populates="items")
    purchase_order_item = db.relationship(
        "PurchaseOrderItem",
        back_populates="goods_receipt_items"
    )


class ComponentMovement(db.Model):
    __tablename__ = "component_movements"

    id = db.Column(db.Integer, primary_key=True)

    goods_receipt_id = db.Column(
        db.Integer,
        db.ForeignKey("goods_receipts.id"),
        nullable=False
    )

    component_id = db.Column(
        db.Integer,
        db.ForeignKey("components.id"),
        nullable=False
    )

    quantity = db.Column(db.Integer, nullable=False)
    movement_type = db.Column(db.String(20), nullable=False, default="IN")
    movement_date = db.Column(db.DateTime, nullable=False, default=datetime.now)

    component = db.relationship("Component", back_populates="movements")
    goods_receipt = db.relationship("GoodsReceipt")


class SupplierInvoice(db.Model):
    __tablename__ = "supplier_invoices"

    id = db.Column(db.Integer, primary_key=True)

    invoice_number = db.Column(db.String(50), nullable=False, unique=True)

    goods_receipt_id = db.Column(
        db.Integer,
        db.ForeignKey("goods_receipts.id"),
        nullable=False,
        unique=True
    )

    supplier_id = db.Column(
        db.Integer,
        db.ForeignKey("suppliers.id"),
        nullable=False
    )

    invoice_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date, nullable=False)

    total_net_amount = db.Column(db.Float, nullable=False, default=0)
    total_vat_amount = db.Column(db.Float, nullable=False, default=0)
    total_gross_amount = db.Column(db.Float, nullable=False, default=0)

    status = db.Column(db.String(50), nullable=False, default="ERFASST")

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    transmitted_at = db.Column(db.DateTime)

    goods_receipt = db.relationship("GoodsReceipt", back_populates="supplier_invoice")
    supplier = db.relationship("Supplier", back_populates="supplier_invoices")

    items = db.relationship(
        "SupplierInvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan"
    )


class SupplierInvoiceItem(db.Model):
    __tablename__ = "supplier_invoice_items"

    id = db.Column(db.Integer, primary_key=True)

    supplier_invoice_id = db.Column(
        db.Integer,
        db.ForeignKey("supplier_invoices.id"),
        nullable=False
    )

    component_id = db.Column(
        db.Integer,
        db.ForeignKey("components.id"),
        nullable=False
    )

    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    unit_discount_pct = db.Column(db.Float, nullable=False, default=0)
    unit_vat_pct = db.Column(db.Float, nullable=False, default=19)

    invoice = db.relationship("SupplierInvoice", back_populates="items")
    component = db.relationship("Component")

    @property
    def net_amount(self):
        discount_factor = 1 - (self.unit_discount_pct / 100)
        return self.quantity * self.unit_price * discount_factor

    @property
    def vat_amount(self):
        return self.net_amount * (self.unit_vat_pct / 100)

    @property
    def gross_amount(self):
        return self.net_amount + self.vat_amount

class EventLog(db.Model):
    __tablename__ = "event_logs"

    id = db.Column(db.Integer, primary_key=True)

    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)

    action = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)

    created_by = db.Column(db.String(50), nullable=False, default="demo_user")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

class ReturnNotification(db.Model):
    __tablename__ = "return_notifications"

    id = db.Column(db.Integer, primary_key=True)

    return_number = db.Column(db.String(50), nullable=False, unique=True)

    goods_receipt_id = db.Column(
        db.Integer,
        db.ForeignKey("goods_receipts.id"),
        nullable=False,
        unique=True
    )

    supplier_id = db.Column(
        db.Integer,
        db.ForeignKey("suppliers.id"),
        nullable=False
    )

    reason = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(50), nullable=False, default="ERSTELLT")

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    sent_at = db.Column(db.DateTime)

    goods_receipt = db.relationship("GoodsReceipt", back_populates="return_notification")
    supplier = db.relationship("Supplier")