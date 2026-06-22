from datetime import datetime, date
from app.extensions import db


class Supplier(db.Model):
    __tablename__ = "T_SUPPLIERS"
    __table_args__ = {"schema": "dbo"}

    id = db.Column("SUPPLIER_ID", db.Integer, primary_key=True)
    name = db.Column("SUPPLIER_NAME", db.String(100), nullable=False)
    country = db.Column("COUNTRY", db.String(100))
    email = db.Column("SUPPLIER_EMAIL", db.String(150))
    website = db.Column("WEBSITE", db.String(200))
    purchase_orders = db.relationship(
    "PurchaseOrder",
    back_populates="supplier",
    lazy=True
)

    purchase_orders = db.relationship(
        "PurchaseOrder",
        back_populates="supplier",
        lazy=True
    )

    supplier_invoices = db.relationship(
    "SupplierInvoice",
    back_populates="supplier",
    lazy=True
    )   


class Component(db.Model):
    __tablename__ = "T_BIKE_COMPONENTS"
    __table_args__ = {"schema": "dbo"}
    
    id = db.Column("COMPONENT_ID", db.Integer, primary_key=True)
    component_group = db.Column("COMPONENT_GROUP", db.String(100))
    name = db.Column("COMPONENT_NAME", db.String(100), nullable=False)
    supplier_id = db.Column(
    "SUPPLIER_ID",
    db.Integer,
    db.ForeignKey("dbo.T_SUPPLIERS.SUPPLIER_ID")
)
    delivery_days = db.Column("DELIVERY_DAYS", db.Integer)
    price = db.Column("COMPONENT_PRICE", db.Numeric(19, 4))
    stock = db.Column("COMPONENT_STOCK", db.Integer, nullable=False, default=0)
    vat = db.Column("VAT", db.Numeric(10, 2))

    order_items = db.relationship("PurchaseOrderItem", back_populates="component", lazy=True)
    movements = db.relationship("ComponentMovement", back_populates="component", lazy=True)
    invoice_items = db.relationship("SupplierInvoiceItem", back_populates="component", lazy=True)

    @property
    def component_number(self):
        return str(self.id)


class PurchaseOrder(db.Model):
    __tablename__ = "T_PO"
    __table_args__ = {"schema": "dbo"}

    id = db.Column("PO_ID", db.Integer, primary_key=True)
    status = db.Column("PO_STATUS", db.Integer)
    supplier = db.relationship(
    "Supplier",
    back_populates="purchase_orders"
)
    supplier_id = db.Column(
    "SUPPLIER_ID",
    db.Integer,
    db.ForeignKey("dbo.T_SUPPLIERS.SUPPLIER_ID")
)
    positions = db.Column("POSITIONS", db.Integer)
    created_at = db.Column("INS_DATE", db.DateTime)
    updated_at = db.Column("UPD_DATE", db.DateTime)

    items = db.relationship(
        "PurchaseOrderItem",
        back_populates="purchase_order",
        lazy=True
    )

    goods_receipts = db.relationship(
        "GoodsReceipt",
        back_populates="purchase_order",
        lazy=True
    )

    supplier_invoices = db.relationship(
    "SupplierInvoice",
    back_populates="purchase_order",
    lazy=True
    )

    @property
    def order_number(self):
        return str(self.id)
    
    @property
    def total_ordered_quantity(self):
        return sum((item.quantity_ordered or 0) for item in self.items)

    @property
    def total_received_quantity(self):
        total = 0

        for receipt in self.goods_receipts:
            for item in receipt.items:
                total += item.quantity_received or 0

        return total

    @property
    def total_open_quantity(self):
        return max(self.total_ordered_quantity - self.total_received_quantity, 0)


class PurchaseOrderItem(db.Model):
    __tablename__ = "T_PO_ITEMS"
    __table_args__ = {"schema": "dbo"}

    id = db.Column("PO_ITEM_ID", db.Integer, primary_key=True)

    purchase_order_id = db.Column(
        "PO_ID",
        db.Integer,
        db.ForeignKey("dbo.T_PO.PO_ID"),
        nullable=False
    )

    purchase_id = db.Column("PURCHASE_ID", db.Integer)
    requested_by = db.Column("REQUESTED_BY", db.String(100))

    component_id = db.Column(
        "ID_COMPONENT",
        db.Integer,
        db.ForeignKey("dbo.T_BIKE_COMPONENTS.COMPONENT_ID")
    )

    delivery_date = db.Column("DELIVERY_DATE", db.Date)
    quantity_ordered = db.Column("QUANTITY", db.Integer)
    component_price = db.Column("COMPONENT_PRICE", db.Numeric(19, 4))
    total_price = db.Column("TOTAL_PRICE", db.Numeric(19, 4))
    status = db.Column("STATUS", db.Integer)

    purchase_order = db.relationship(
        "PurchaseOrder",
        back_populates="items"
    )

    component = db.relationship(
        "Component",
        back_populates="order_items"
    )

    @property
    def quantity_received(self):
        total = db.session.query(
            db.func.coalesce(db.func.sum(GoodsReceiptItem.quantity_received), 0)
        ).filter(
            GoodsReceiptItem.purchase_order_id == self.purchase_order_id,
            GoodsReceiptItem.purchase_order_item_id == self.id
        ).scalar()

        return int(total or 0)


class GoodsReceipt(db.Model):
    __tablename__ = "T_GOODS_RECEIPT"
    __table_args__ = {"schema": "dbo"}

    id = db.Column("GOODS_RECEIPT_ID", db.Integer, primary_key=True)
    purchase_order_id = db.Column(
    "PO_ID",
    db.Integer,
    db.ForeignKey("dbo.T_PO.PO_ID"),
    nullable=False
)
    receipt_date = db.Column("RECEIPT_DATE", db.DateTime)
    receipt_number = db.Column("DELIVERY_NOTE_NUMBER", db.String(100))
    status = db.Column("STATUS", db.Integer)

    items = db.relationship(
        "GoodsReceiptItem",
        back_populates="goods_receipt",
        lazy=True
    )

    purchase_order = db.relationship(
    "PurchaseOrder",
    back_populates="goods_receipts"
    )

    movements = db.relationship(
    "ComponentMovement",
    back_populates="goods_receipt",
    lazy=True
)

    @property
    def note(self):
        return ""

    @property
    def supplier_invoice(self):
        if self.purchase_order and self.purchase_order.supplier_invoices:
            return self.purchase_order.supplier_invoices[0]
        return None

class GoodsReceiptItem(db.Model):
    __tablename__ = "T_GOODS_RECEIPT_ITEM"
    __table_args__ = {"schema": "dbo"}

    id = db.Column("GOODS_RECEIPT_ITEM_ID", db.Integer, primary_key=True)

    goods_receipt_id = db.Column(
        "GOODS_RECEIPT_ID",
        db.Integer,
        db.ForeignKey("dbo.T_GOODS_RECEIPT.GOODS_RECEIPT_ID"),
        nullable=False
    )

    purchase_order_id = db.Column("PO_ID", db.Integer)
    purchase_order_item_id = db.Column("PO_ITEM_ID", db.Integer)
    quantity_ordered = db.Column("ORDERED_QTY", db.Integer)
    quantity_received = db.Column("RECEIVED_QTY", db.Integer)
    condition_id = db.Column("CONDITION_ID", db.Integer)

    goods_receipt = db.relationship(
        "GoodsReceipt",
        back_populates="items"
    )


class ComponentMovement(db.Model):
    __tablename__ = "T_COMPONENTS_MOVEMENTS"
    __table_args__ = {"schema": "dbo"}

    id = db.Column("MOVEMENT_ID", db.Integer, primary_key=True)

    goods_receipt_id = db.Column(
        "GOODS_RECEIPT_ID",
        db.Integer,
        db.ForeignKey("dbo.T_GOODS_RECEIPT.GOODS_RECEIPT_ID")
    )

    component_id = db.Column(
        "COMPONENT_ID",
        db.Integer,
        db.ForeignKey("dbo.T_BIKE_COMPONENTS.COMPONENT_ID"),
        nullable=False
    )

    mtb_component_id = db.Column("MTB_COMPONENT_ID", db.Integer)
    quantity = db.Column("QUANTITY", db.Integer)
    movement_type = db.Column("MOVEMENT_TYPE", db.Integer)
    movement_date = db.Column("MOVEMENT_DATE", db.DateTime)

    component = db.relationship(
        "Component",
        back_populates="movements"
    )

    goods_receipt = db.relationship(
        "GoodsReceipt",
        back_populates="movements"
    )


class SupplierInvoice(db.Model):
    __tablename__ = "T_SUPPLIER_INVOICE"
    __table_args__ = {"schema": "dbo"}

    id = db.Column("INVOICE_ID", db.Integer, primary_key=True)

    purchase_order_id = db.Column(
        "PO_ID",
        db.Integer,
        db.ForeignKey("dbo.T_PO.PO_ID")
    )

    invoice_date = db.Column("INVOICE_DATE", db.Date)
    due_date = db.Column("DUE_DATE", db.Date)
    payment_terms = db.Column("PAYMENT_TERMS", db.Integer)
    status = db.Column("INVOICE_STATUS", db.Integer)

    created_by = db.Column("INS_USER", db.String(100))
    created_at = db.Column("INS_DATE", db.DateTime)
    updated_by = db.Column("UPD_USER", db.String(100))
    updated_at = db.Column("UPD_DATE", db.DateTime)

    supplier_id = db.Column(
        "SUPPLIER_ID",
        db.Integer,
        db.ForeignKey("dbo.T_SUPPLIERS.SUPPLIER_ID")
    )

    total_net_amount = db.Column("TOTAL_NET_AMOUNT", db.Numeric(19, 4))
    total_vat_amount = db.Column("TOTAL_VAT_AMOUNT", db.Numeric(19, 4))
    total_gross_amount = db.Column("TOTAL_GROSS_AMOUNT", db.Numeric(19, 4))

    purchase_order = db.relationship(
        "PurchaseOrder",
        back_populates="supplier_invoices"
    )

    supplier = db.relationship(
        "Supplier",
        back_populates="supplier_invoices"
    )

    items = db.relationship(
        "SupplierInvoiceItem",
        back_populates="invoice",
        lazy=True
    )

    @property
    def invoice_number(self):
        return str(self.id)

    @property
    def goods_receipt(self):
        if self.purchase_order and self.purchase_order.goods_receipts:
            return self.purchase_order.goods_receipts[0]
        return None


class SupplierInvoiceItem(db.Model):
    __tablename__ = "T_SUPPLIER_INVOICE_ITEM"
    __table_args__ = {"schema": "dbo"}

    invoice_id = db.Column(
        "INVOICE_ID",
        db.Integer,
        db.ForeignKey("dbo.T_SUPPLIER_INVOICE.INVOICE_ID"),
        primary_key=True
    )

    id = db.Column("INVOICE_ITEM_ID", db.Integer, primary_key=True)

    material_id = db.Column("ID_MAT", db.Integer)
    quantity = db.Column("QUANTITY", db.Integer)
    unit_price = db.Column("UNIT_PRICE", db.Numeric(19, 4))
    unit_discount_pct = db.Column("UNIT_DISCOUNT_PCT", db.Numeric(10, 2))
    unit_vat_pct = db.Column("UNIT_VAT_PCT", db.Numeric(10, 2))
    unit_net_value = db.Column("UNIT_NET_VALUE", db.Numeric(19, 4))

    component_id = db.Column(
        "COMPONENT_ID",
        db.Integer,
        db.ForeignKey("dbo.T_BIKE_COMPONENTS.COMPONENT_ID")
    )

    mtb_component_id = db.Column("MTB_COMPONENT_ID", db.Integer)

    invoice = db.relationship(
        "SupplierInvoice",
        back_populates="items"
    )

    component = db.relationship(
        "Component",
        back_populates="invoice_items"
    )

class EventLog(db.Model):
    __tablename__ = "T_EVENTLOG"
    __table_args__ = {"schema": "dbo"}

    id = db.Column("EventLogID", db.Integer, primary_key=True)
    entity_type = db.Column("TableName", db.String(100))
    entity_id = db.Column("RecordID", db.Integer)
    action = db.Column("EventType", db.String(50))
    created_at = db.Column("EventTime", db.DateTime)
    created_by = db.Column("ChangedBy", db.String(100))

    old_data = db.Column("OldData", db.Text)
    new_data = db.Column("NewData", db.Text)

    @property
    def description(self):
        return self.new_data or self.old_data or "-"

class ReturnNotification(db.Model):
    __tablename__ = "return_notifications"

    id = db.Column(db.Integer, primary_key=True)

    return_number = db.Column(db.String(50), nullable=False, unique=True)

    #goods_receipt_id = db.Column(db.Integer, nullable=False, unique=True)

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

    #goods_receipt = db.relationship("GoodsReceipt", back_populates="return_notification")
    #supplier = db.relationship("Supplier")